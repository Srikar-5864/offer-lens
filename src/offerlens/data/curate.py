"""Stage 1b: curate teacher-written rows with CuratorKIT into trainer-ready sft_messages.

CuratorKIT 0.1.22 API used (verified with inspect.signature(CuratorConfig)):
  CuratorConfig(dataset, dedup="minhash", minhash_threshold, clean, clean_transforms={"strip_html": False},
                secrets_gate, judge_llm_model, judge_llm_api_base, reward_threshold, reward_prompt_template,
                reward_dimensions, judge_on_error, judge_concurrency, export_formats=["messages"], output_split,
                output_dir, min_tokens)
  Curator(cfg).run() -> CuratorResult; writes sft_messages.jsonl, manifest.json, rejected.jsonl,
  dataset_card.md, checksums.txt.
strip_html is disabled: it deletes our <offer_text> delimiters and would make the training prompt differ
from inference (found in the H1 smoke test).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date

from offerlens import prompt
from offerlens.schema import Extraction, to_json
from offerlens.settings import ROOT, get_settings, load_config

JUDGE_PROMPT = """You check a data-extraction training example. The instruction contains an Indian shopping \
offer between <offer_text> tags; the response is the JSON extracted from it.

Instruction: {instruction}

Response: {response}

Score 1.0 if every value in the JSON is stated in (or directly resolvable from) the offer text, nothing stated \
in the text is missing, and unstated fields are null/empty. Lower the score for each wrong, invented or missing \
value. Ignore formatting and key order.

Respond in JSON format ONLY:
{{"instruction_following": 0.XX, "truthfulness": 0.XX, "overall_score": 0.XX, "reason": "<short>"}}"""


def build_sft_ready() -> int:
    cfg = load_config("data")
    raw = ROOT / cfg["raw_dir"]
    rows = [json.loads(line) for line in (raw / "offers.jsonl").read_text().splitlines() if line]
    with (raw / "sft_ready.jsonl").open("w") as fh:
        for r in rows:
            gold = Extraction.model_validate(r["gold"])
            msgs = prompt.messages(r["text"], date.fromisoformat(r["reference_date"]))
            msgs.append({"role": "assistant", "content": to_json(gold)})
            fh.write(json.dumps({"id": r["id"], "messages": msgs}, ensure_ascii=False) + "\n")
    return len(rows)


def check_export(path_glob: str) -> int:
    """Every exported row must keep the exact prompt contract and a schema-valid target."""
    n = 0
    for path in (ROOT / load_config("data")["curated_dir"]).glob(path_glob):
        for line in path.read_text().splitlines():
            msgs = json.loads(line)["messages"]
            assert msgs[0] == {"role": "system", "content": prompt.SYSTEM}, "system prompt drifted"
            assert (
                msgs[1]["content"].startswith("reference_date: ") and "<offer_text>\n" in msgs[1]["content"]
            )
            Extraction.model_validate_json(msgs[2]["content"])
            n += 1
    return n


def main() -> None:
    from curatorkit import Curator, CuratorConfig

    cfg = load_config("data")
    settings = get_settings()
    n_in = build_sft_ready()
    out = ROOT / cfg["curated_dir"]
    result = Curator(
        CuratorConfig(
            dataset=str(ROOT / cfg["raw_dir"] / "sft_ready.jsonl"),
            name="offerlens",
            min_tokens=5,
            clean=True,
            clean_transforms={"strip_html": False},
            dedup="minhash",
            minhash_threshold=0.85,
            secrets_gate=True,
            judge_llm_model="openai/teacher",
            judge_llm_api_base=settings.base_url("teacher"),
            llm_api_key=settings.sglang_api_key.get_secret_value() if settings.sglang_api_key else "none",
            reward_threshold=cfg["reward_threshold"],
            reward_prompt_template=JUDGE_PROMPT,
            reward_dimensions=["instruction_following", "truthfulness"],
            judge_on_error="reject",
            judge_concurrency=16,
            judge_llm_max_tokens=120,
            export_formats=["messages"],
            output_split=cfg["split"],
            output_dir=str(out),
        )
    ).run()
    result.print_summary()
    manifest = json.loads((out / "manifest.json").read_text())
    reasons = Counter(
        json.loads(line).get("gate", json.loads(line).get("step", "?"))
        for line in (out / "rejected.jsonl").read_text().splitlines()
        if line
    )
    n_out = check_export("**/sft_messages.jsonl")
    summary = {"input_rows": n_in, "exported_rows": n_out, "rejected_by_gate": dict(reasons)}
    summary["near_duplicates_removed"] = manifest.get("dedup_stats", {}).get("near_duplicates_removed")
    (out / "curation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
