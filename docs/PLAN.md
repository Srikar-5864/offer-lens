# Build plan — 4.5 hours, with checkpoints

Rule: if a checkpoint is missed by >20 min, take the listed **fallback** and move on.
Long jobs run in the background (`nohup ... &` / `make ... &`); build the next stage while they run.

## H0 · 0:00–0:30 — Environment & risk burn-down
- `nvidia-smi` → record GPU + VRAM in `docs/DECISIONS.md`. Pick teacher by VRAM:
  - ≥40 GB: `Qwen/Qwen2.5-14B-Instruct` · 24 GB: `Qwen/Qwen2.5-7B-Instruct` · <24 GB: 7B AWQ/int4
- `uv init`, add deps, scaffold repo layout from `docs/SPEC.md`, `pre-commit install`.
- Install & smoke-test each kit **with its own quickstart** (skills have commands):
  `sglang` (serve teacher, one chat call), `curatorkit`, `aligntune`, `auditkit`.
- ✅ Checkpoint: teacher answers a constrained-JSON request on 127.0.0.1:30000.

## H1 · 0:30–1:30 — Stage 1 data (skill: `curate-offers`)
- Write `src/offerlens/schema.py` (Pydantic, from SPEC) + `schema.json` export + unit tests.
- Write seed generators: ~60 merchants, ~25 issuers, 8 style templates (see DATA.md).
- Generate ~2,000 raw offers + gold JSON via SGLang teacher (constrained to schema). Run in background.
- Meanwhile: hand-label **30 real offers** from DealFeed into `data/real/real_test.jsonl` (gitignored).
- Curate with CuratorKIT: clean → minhash dedup → hygiene (PII) → judge gate → export `sft_messages`,
  split 90/10. Hold out 200 synthetic for test.
- ✅ Checkpoint: `data/curated/` loads with `load_dataset(path, "sft_messages")`, ≥1,200 train rows.
- Fallback: if CuratorKIT generation path fights you, generate with our own script and use CuratorKIT only
  for clean/dedup/hygiene/export. Document it.

## H2 · 1:30–2:30 — Stage 2 training (skill: `finetune-aligntune`)
- AlignTune `create_sft_trainer`, backend `unsloth`, LoRA r=16, 2 epochs, max_seq_len 1024.
- Start training in background (~20–40 min). Log to `reports/train_log.json`.
- **While training:** build the eval harness (H3 tasks) and the FastAPI skeleton + UI shell (H3.5).
- Merge LoRA → `models/offerlens-1.5b-merged`.
- ✅ Checkpoint: merged model serves on 127.0.0.1:30001 and returns valid JSON.
- Fallback: backend `trl` if unsloth install fails; 1 epoch if time is short.

## H3 · 2:30–3:30 — Stage 3 eval (skill: `eval-auditkit`)
- Run conditions A, B, C (and D=teacher if time) on synthetic test + real test.
- Metrics per EVAL.md → `reports/results.json`, `reports/errors.jsonl`.
- `make report` writes README table + `reports/chart.svg`.
- ✅ Checkpoint: numbers exist for A/B/C on both test sets.

## H3.5 · 3:30–4:15 — Demo app (skill: `offerlens-ui`)
- FastAPI + static HTML/CSS/JS (no build step). Three views: Extract, Compare, Results.
- Apply SECURITY.md controls (skill: `security-review`).
- ✅ Checkpoint: DESIGN.md checklist passes in the browser at 375px and 1440px.

## H4.15 · 4:15–4:45 — Ship (skill: `ship-demo`)
- `make check` green, README results + Known gaps, record a 60s backup screen capture of the demo.
- Rehearse `docs/DEMO_SCRIPT.md` twice.

## Cut list (drop in this order if behind)
1. Condition D (teacher reference) 2. Compare view 3. Cost calculator slider 4. Hinglish style templates beyond 2
**Never cut:** real test set, condition B vs C split, Known gaps section.
