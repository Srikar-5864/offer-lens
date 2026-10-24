"""Stage 3: run conditions A/B/C/D on every test set through AuditKIT, then a throughput benchmark.

AuditKIT 1.1.3 API used: ak.evaluate(samples, model=<list[str] -> list[str] callable>, scorers=[@ak.scorer...],
config=ak.RunConfig(...)). The callable is our SGLang client, so response_format=json_schema and the exact
prompt module are used (AuditKIT's OpenAI adapter can't pass response_format; see EVAL.md Known gaps).

Only conditions whose SGLang server is up are run; results.json is merged, so servers can be started one at a
time on a 16 GB machine:  make serve-base & make eval;  make serve-student & make eval;  ...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess  # nosec B404 - fixed argv, used only for git sha
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from offerlens import prompt, sglang_client
from offerlens.eval import metrics
from offerlens.schema import Extraction
from offerlens.settings import ROOT, Role, get_settings, load_config

REPORTS = ROOT / "reports"


def load_set(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def _predict(
    rows: list[dict[str, Any]], role: Role, constrained: bool, conc: int, timeout: float
) -> list[Any]:
    sem = asyncio.Semaphore(conc)
    async with httpx.AsyncClient() as client:

        async def one(r: dict[str, Any]) -> Any:
            async with sem:
                try:
                    return await sglang_client.aextract(
                        client,
                        role,
                        r["text"],
                        date.fromisoformat(r["reference_date"]),
                        constrained=constrained,
                        timeout=timeout,
                    )
                except httpx.HTTPError as exc:
                    return sglang_client.Result(
                        raw=f"<error {type(exc).__name__}>", extraction=None, latency_ms=0
                    )

        return await asyncio.gather(*(one(r) for r in rows))


def run_condition(
    cond: str, spec: dict[str, Any], name: str, rows: list[dict[str, Any]], cfg: dict[str, Any]
) -> dict[str, Any]:
    import auditkit as ak

    results: dict[str, sglang_client.Result] = {}

    def model(inputs: list[str]) -> list[str]:
        batch = [json.loads(i) for i in inputs]
        outs = asyncio.run(
            _predict(batch, spec["role"], spec["constrained"], cfg["concurrency"], cfg["timeout_s"])
        )
        for b, o in zip(batch, outs, strict=True):
            results[b["id"]] = o
        return [o.raw for o in outs]

    def _pair(sample: Any, output: str) -> tuple[Extraction, Extraction | None]:
        return Extraction.model_validate_json(str(sample.target)), sglang_client.parse(output)

    @ak.scorer(direction=ak.Direction.MAXIMIZE, name="schema_valid")
    def schema_valid(sample: Any, output: str) -> float:
        return float(_pair(sample, output)[1] is not None)

    @ak.scorer(direction=ak.Direction.MAXIMIZE, name="field_acc")
    def field_acc(sample: Any, output: str) -> float:
        return metrics.score(*_pair(sample, output)).field_acc

    @ak.scorer(direction=ak.Direction.MAXIMIZE, name="exact_record")
    def exact_record(sample: Any, output: str) -> float:
        return float(metrics.score(*_pair(sample, output)).exact)

    samples = [
        ak.Sample(
            input=json.dumps({"id": r["id"], "text": r["text"], "reference_date": r["reference_date"]}),
            target=json.dumps(r["gold"]),
            id=r["id"],
            task=f"offerlens-{name}",
        )
        for r in rows
    ]
    run = ak.evaluate(
        samples,
        model,
        scorers=[schema_valid, field_acc, exact_record],
        config=ak.RunConfig(batch_size=len(samples), concurrency=1, temperature=0.0, max_tokens=512),
        experiment_name=f"offerlens-{cond}-{name}",
        tags=[cond, name, prompt.PROMPT_VERSION],
    )
    out_dir = REPORTS / "runs" / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    run.save(str(out_dir / f"{name}.auditkit.json"))

    scores, errors = [], []
    for r in rows:
        res = results[r["id"]]
        gold = Extraction.model_validate(r["gold"])
        s = metrics.score(gold, res.extraction)
        scores.append(s)
        if not s.exact:
            errors.append({
                "condition": cond, "test_set": name, "id": r["id"], "style": r.get("style"), "text": r["text"],
                "reference_date": r["reference_date"], "gold": r["gold"], "pred_raw": res.raw[:2000],
                "valid": s.valid, "failing_fields": s.failing_fields,
            })  # fmt: skip
    summary: dict[str, Any] = metrics.summarize(scores)
    summary["auditkit_headline"] = run.headline
    summary["auditkit_run_id"] = run.run_id
    lat = [results[r["id"]].latency_ms for r in rows]
    summary["eval_latency_p50_ms"] = metrics.percentile(lat, 0.5)
    summary["avg_prompt_tokens"] = sum(results[r["id"]].prompt_tokens for r in rows) / len(rows)
    summary["avg_completion_tokens"] = sum(results[r["id"]].completion_tokens for r in rows) / len(rows)
    with (out_dir / f"{name}.errors.jsonl").open("w") as fh:
        fh.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in errors)
    return summary


async def bench(
    role: Role, constrained: bool, rows: list[dict[str, Any]], n: int, conc: int
) -> dict[str, float]:
    """Latency/throughput with `conc` concurrent requests after a 10-request warm-up."""
    pool = (rows * (n // max(1, len(rows)) + 1))[:n]
    await _predict(pool[:10], role, constrained, conc, 120)
    t0 = time.perf_counter()
    outs = await _predict(pool, role, constrained, conc, 120)
    wall = time.perf_counter() - t0
    lat = [o.latency_ms for o in outs]
    return {
        "latency_p50_ms": metrics.percentile(lat, 0.5),
        "latency_p95_ms": metrics.percentile(lat, 0.95),
        "throughput_rps": len(pool) / wall,
        "bench_requests": len(pool),
        "bench_concurrency": conc,
    }


def git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True
        )  # nosec
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default="A,B,C,D")
    ap.add_argument("--sets", default=None, help="comma list; default all present")
    ap.add_argument("--no-bench", action="store_true")
    args = ap.parse_args()
    cfg = load_config("eval")
    settings = get_settings()
    results_path = REPORTS / "results.json"
    results: dict[str, Any] = json.loads(results_path.read_text()) if results_path.exists() else {}
    sets = {k: ROOT / v for k, v in cfg["test_sets"].items() if (ROOT / v).exists()}
    if args.sets:
        sets = {k: v for k, v in sets.items() if k in args.sets.split(",")}
    print("test sets:", {k: len(load_set(v)) for k, v in sets.items()})

    async def up(role: Role) -> bool:
        async with httpx.AsyncClient() as c:
            return await sglang_client.healthy(c, role)

    all_errors: list[str] = []
    for cond in args.conditions.split(","):
        spec = cfg["conditions"][cond]
        if not asyncio.run(up(spec["role"])):
            print(f"[{cond}] {spec['role']} server not up — skipped")
            continue
        block = results.setdefault(cond, {})
        block["_spec"] = spec
        for name, path in sets.items():
            print(f"[{cond}] {name} …", flush=True)
            block[name] = run_condition(cond, spec, name, load_set(path), cfg)
            print(
                f"[{cond}] {name}: {json.dumps({k: round(v, 3) for k, v in block[name].items() if isinstance(v, float)})}"
            )
        if not args.no_bench and "synthetic" in sets:
            perf = asyncio.run(
                bench(
                    spec["role"],
                    spec["constrained"],
                    load_set(sets["synthetic"]),
                    cfg["bench_requests"],
                    cfg["concurrency"],
                )
            )
            if settings.gpu_cost_inr_per_hour:
                perf["cost_per_1k_inr"] = metrics.cost_per_1k_inr(
                    settings.gpu_cost_inr_per_hour, perf["throughput_rps"]
                )
            block["perf"] = perf
            print(f"[{cond}] perf: {perf}")
    for cond in results:
        if cond != "meta":
            all_errors += [
                p.read_text() for p in sorted((REPORTS / "runs" / cond).glob("*.errors.jsonl")) if cond == "C"
            ]
    models = load_config("models")
    results["meta"] = {
        "git_sha": git_sha(),
        "prompt_version": prompt.PROMPT_VERSION,
        "model_revisions": {k: v.get("revision", v.get("path")) for k, v in models.items()},
        "n": {k: len(load_set(v)) for k, v in sets.items()},
        "updated": datetime.now(UTC).isoformat(timespec="seconds"),
        "hardware": "Apple M4 (10-core GPU), 16 GB unified memory, SGLang MLX backend",
        "closed_api": cfg.get("closed_api"),
        "gpu_cost_inr_per_hour": settings.gpu_cost_inr_per_hour,
    }
    REPORTS.mkdir(exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    (REPORTS / "errors.jsonl").write_text("".join(all_errors))
    print(f"wrote {results_path}")


if __name__ == "__main__":
    main()
