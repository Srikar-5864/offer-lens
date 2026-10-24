---
name: curate-offers
description: Stage 1 of OfferLens — generate synthetic Indian deal/cashback offers with gold JSON via the SGLang teacher and curate them with CuratorKIT into trainer-ready sft_messages. Use when building or changing anything under src/offerlens/data or data/.
---

# Curate offers (Stage 1)

Read `docs/DATA.md` first. It is the spec; this skill is the procedure.

## 0. Verify CuratorKIT API (5 min, do not skip)
```bash
pip install "curatorkit[all]"            # Python ≥ 3.11
python -c "import curatorkit, inspect; print(curatorkit.__version__); from curatorkit import CuratorConfig; print(inspect.signature(CuratorConfig))"
```
Skim https://curatorkit.lexsi.ai/latest/ (configuration reference, CLI & YAML) and the repo's examples/quickstart.
Write the real parameter names you'll use into a comment at the top of `curate.py`.

## 1. Spec-first generation (`seeds.py`, `generate.py`)
- Sample ground-truth `Extraction` objects in Python with a seeded RNG (seed 42 train, seed 7 test — separate seeds = no leakage).
- Ask the SGLang teacher (port 30000, temp 0.9) to *write* offer text for the spec in the chosen style template.
- Round-trip verify: teacher extracts from its own text (constrained, temp 0); drop if >1 field disagrees with spec.
- Write `data/raw/offers.jsonl` rows: `{id, style, reference_date, text, gold}`. Use asyncio with concurrency 32.

## 2. CuratorKIT pass (`curate.py`)
Expected shape (confirm names in step 0):
```python
from curatorkit import Curator, CuratorConfig
result = Curator(CuratorConfig(
    dataset="data/raw/sft_ready.jsonl",       # rows already in chat-messages form
    clean=True, dedup="minhash",
    llm_model="openai/teacher", llm_api_base="http://127.0.0.1:30000/v1",   # LiteLLM → SGLang
    judge_llm_model="openai/teacher", reward_threshold=0.7, judge_on_error="reject",
    export_formats=["messages"], output_split={"train": 0.9, "validation": 0.1},
    output_dir="data/curated",
)).run()
result.print_summary()
```
- Enable hygiene gates (PII/secrets) — mandatory for anything derived from real DealFeed text.
- Confirm load: `datasets.load_dataset("data/curated", "sft_messages")`.
- Keep `manifest.json` + `rejected.jsonl`; print rejection counts by reason for the deck.

## 3. Fallback
If generation/judging through CuratorKIT fails, keep our generation script and use CuratorKIT for
clean + dedup + hygiene + export only. Log it in `docs/DECISIONS.md` and EVAL.md "Known gaps".

## Done when
≥1,200 train rows, 200-row synthetic test from seed 7, 30 real test rows, manifest saved, `pytest tests/test_schema.py` green.
