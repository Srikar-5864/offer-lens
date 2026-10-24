"""`make report`: README results table + reports/chart.svg from reports/results.json (never hand-edited)."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any
from xml.sax.saxutils import escape

from offerlens.settings import ROOT

REPORTS = ROOT / "reports"
NAMES = {
    "A": "A. Base, unconstrained",
    "B": "B. Base + constrained",
    "C": "C. Fine-tuned + constrained",
    "D": "D. Teacher 7B + constrained",
}
COLORS = {"A": "#141414", "B": "#1446A0", "C": "#D7261E", "D": "#5B574F"}
CHART_METRICS = [
    ("schema_valid", "Schema-valid"),
    ("field_acc", "Field accuracy"),
    ("hallucination_rate", "Hallucinated fields"),
]


def _pct(v: Any) -> str:
    return f"{100 * v:.1f}%" if isinstance(v, int | float) else "—"


def table(results: dict[str, Any], test_set: str) -> str:
    rows = [
        "| Condition | Schema-valid | Field accuracy | Hallucinated fields | p50 latency | Cost / 1k |",
        "|---|---|---|---|---|---|",
    ]
    for cond, name in NAMES.items():
        m = results.get(cond, {}).get(test_set)
        if not m:
            continue
        perf = results[cond].get("perf", {})
        lat = f"{perf['latency_p50_ms']:.0f} ms" if "latency_p50_ms" in perf else "—"
        cost = f"₹{perf['cost_per_1k_inr']:.2f}" if "cost_per_1k_inr" in perf else "—"
        rows.append(
            f"| {name} | {_pct(m['schema_valid'])} | {_pct(m['field_acc'])} | {_pct(m['hallucination_rate'])} | {lat} | {cost} |"
        )
    return "\n".join(rows)


def chart(results: dict[str, Any], test_set: str) -> str:
    conds = [c for c in NAMES if results.get(c, {}).get(test_set)]
    w, row_h, bar_h, left = 640, 34 * max(1, len(conds)) + 40, 26, 170
    h = row_h * len(CHART_METRICS) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Archivo, sans-serif" font-size="13">',
           f'<rect width="{w}" height="{h}" fill="#F3EEE3"/>']  # fmt: skip
    for i, (key, label) in enumerate(CHART_METRICS):
        y0 = 20 + i * row_h
        out.append(f'<text x="0" y="{y0 + 14}" font-weight="800" fill="#141414">{escape(label)}</text>')
        for j, c in enumerate(conds):
            v = float(results[c][test_set][key])
            y = y0 + 24 + j * (bar_h + 6)
            bw = max(1.0, (w - left - 70) * v)
            out.append(f'<text x="0" y="{y + 18}" fill="#5B574F">{c}</text>')
            out.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="{COLORS[c]}"/>')
            out.append(f'<text x="{left + bw + 6:.1f}" y="{y + 18}" fill="#141414">{_pct(v)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    results = json.loads((REPORTS / "results.json").read_text())
    blocks = []
    for test_set in ("synthetic", "handlabeled", "real", "injection"):
        if any(results.get(c, {}).get(test_set) for c in NAMES):
            n = results.get("meta", {}).get("n", {}).get(test_set, "?")
            blocks.append(f"**{test_set} test (n={n})**\n\n{table(results, test_set)}")
    readme = ROOT / "README.md"
    body = "\n\n".join(blocks) or "_No results yet — run `make eval`._"
    text = re.sub(
        r"<!-- results:start -->.*<!-- results:end -->",
        f"<!-- results:start -->\n{body}\n<!-- results:end -->",
        readme.read_text(),
        flags=re.S,
    )
    readme.write_text(text)
    if any(results.get(c, {}).get("synthetic") for c in NAMES):
        (REPORTS / "chart.svg").write_text(chart(results, "synthetic") + "\n")
    errors = (
        [json.loads(line) for line in (REPORTS / "errors.jsonl").read_text().splitlines() if line]
        if (REPORTS / "errors.jsonl").exists()
        else []
    )
    buckets = Counter(f.split(".", 1)[-1].split(":")[0] for e in errors for f in e["failing_fields"])
    print("top C error fields:", buckets.most_common(3))


if __name__ == "__main__":
    main()
