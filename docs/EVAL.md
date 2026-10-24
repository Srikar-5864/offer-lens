# Stage 3 — Evaluation (AuditKIT + SGLang)

Docs: https://auditkit.lexsi.ai · repo: https://github.com/Lexsi-Labs/AuditKIT · `pip install "auditkit[openai]"`
AuditKIT supports custom metrics/annotators and SGLang/OpenAI-compatible endpoints; use it as the runner and
register our metrics as custom metrics. Our `metrics.py` stays pure-Python and unit-tested either way.

## Conditions
| ID | Model | Decoding | Purpose |
|---|---|---|---|
| A | base 1.5B | free text, parse JSON | the naive baseline |
| B | base 1.5B | SGLang `response_format=json_schema` | "can grammar alone fix it?" |
| C | fine-tuned 1.5B | SGLang `json_schema` | our system |
| D (opt.) | teacher 7B/14B | `json_schema` | reference ceiling |
All: temperature 0, same prompt module, same test files. Report **synthetic test** and **real test** separately.

## Metrics (`src/offerlens/eval/metrics.py`)
| Metric | Definition |
|---|---|
| `schema_valid` | `Extraction.model_validate_json(out)` succeeds (includes our validators) |
| `field_acc` | mean over scalar fields of normalized exact match (strings casefold+strip, numbers ±0.5, dates exact) |
| `list_f1` | micro-F1 on `payment_modes` and `exclusions` (exclusions via fuzzy match ≥0.8) |
| `offer_count_acc` | predicted number of offers == gold |
| `exact_record` | whole extraction matches |
| `hallucination_rate` | share of fields where gold is null/[] but prediction is non-empty — **headline safety metric** |
| `omission_rate` | gold non-null, prediction null |
| `latency_p50/p95_ms`, `throughput_rps` | measured with 16 concurrent requests against SGLang |
| `cost_per_1k_inr` | GPU ₹/hour ÷ (throughput × 3600) × 1000. Closed-API comparison uses that provider's **current published price**, fetched at build time and cited — never a remembered number |

Offer matching for multi-offer texts: Hungarian matching on field overlap before scoring.

## Outputs
- `reports/results.json` — `{condition: {test_set: {metric: value}}, meta: {git_sha, prompt_version, model_revisions, n}}`
- `reports/errors.jsonl` — every C failure with input, gold, pred, failing fields
- `reports/chart.svg` — grouped bars A/B/C for schema_valid, field_acc, hallucination_rate (flat colors per DESIGN.md)

## Error analysis (10 minutes, worth it)
Bucket C's errors: relative dates, multi-offer, Hinglish numerals ("1.5k", "dedh sau"), caps vs value confusion,
exclusion wording. Top 3 buckets go on a slide. Honest failure cases win judges' trust.

## Known gaps
- **No results yet.** The pipeline is implemented but was stopped before data generation finished (the 7B
  teacher made the 16 GB M4 laptop unusable). `reports/results.json` does not exist, so the README table and the
  Results page show nothing. Run `make data train merge eval report` on a machine with more memory or a GPU.
- **Real DealFeed test set not labelled.** `data/real/real_test.jsonl` (30 hand-labelled real offers) has to be
  built by the team; eval skips any test set whose file is missing.
- **SGLang on Apple Silicon** runs from a source build with the MLX backend. `--mlx-enable-sampling` is required or
  json_schema constraints are silently ignored. Throughput numbers from this machine are not comparable to a GPU.
- **AlignTune**: unsloth backend unavailable (CUDA only) → `trl`. Pinned to 0.1.17 because 0.1.28 pulls vLLM.
- **CuratorKIT**: the default HTML cleaner strips our prompt delimiters; disabled (`strip_html: False`).
- **AuditKIT**: its OpenAI adapter can't send `response_format`, so our SGLang client is the model callable and
  AuditKIT is the runner/scorer/provenance layer.
- **Data verification gate** is a deterministic fact-presence check, not the teacher round-trip in DATA.md
  (see DECISIONS.md). CuratorKIT's LLM judge is the model-based gate.
- **Not done:** unit tests (`tests/`), CI workflow, injection fixture set, cost comparison against a closed API.
