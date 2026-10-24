---
name: eval-auditkit
description: Stage 3 of OfferLens — run the A/B/C (and optional D) evaluation through Lexsi AuditKIT against SGLang endpoints with custom extraction metrics, and write reports/results.json, errors.jsonl and chart.svg. Use for anything under src/offerlens/eval or reports/.
---

# Evaluate with AuditKIT (Stage 3)

Spec: `docs/EVAL.md`. Docs: https://auditkit.lexsi.ai · repo: https://github.com/Lexsi-Labs/AuditKIT

## 0. Verify API
```bash
pip install "auditkit[openai]"
python -c "import auditkit as ak; print(ak.__version__); print([n for n in dir(ak) if not n.startswith('_')])"
auditkit --help
```
Read the notebooks on custom metrics/annotators and the SGLang/OpenAI-compatible model adapter. CuratorKIT
output can be loaded with `from auditkit.loaders import load_hf` (check signature).

## 1. Metrics first, framework second
- Implement `src/offerlens/eval/metrics.py` as pure functions with unit tests (hand-computed expected values) **before** wiring AuditKIT.
- Register them with AuditKIT as custom metrics so runs, outputs and provenance live in AuditKIT's format.
- If an AuditKIT adapter can't pass `response_format`, use our `sglang_client` to produce predictions and feed them to
  AuditKIT for scoring — document in Known gaps.

## 2. Run
`make eval` runs each condition on `synthetic_test` and `real_test`, temperature 0, then the throughput benchmark.
Each run writes into `reports/runs/<condition>/` and aggregates into `reports/results.json` with meta (git sha, prompt version, revisions, n).

## 3. Report
`make report`:
- Rewrites the README results table between `<!-- results:start -->` / `<!-- results:end -->` markers.
- Renders `reports/chart.svg` (flat fills: A=ink, B=blue, C=red; no gradients; direct labels).
- Prints top-3 error buckets from `reports/errors.jsonl`.

## Integrity rules
- Never tune prompts on the real test set. Never hand-edit results.
- Cost comparison: fetch the closed API's current price page at build time, cite URL + date in results meta.
