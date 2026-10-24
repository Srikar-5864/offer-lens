# OfferLens — Claude Code project guide

Hackathon build for **Syntax Error 2026 · Local LLM Track · Problem Statement #5 (Structured output and extraction)**.
Time budget: **4–5 hours total**. Ship a working, honest, well-measured thing over an ambitious broken one.

## What we are building
A small open model (Qwen2.5-1.5B-Instruct, LoRA fine-tuned) that turns messy Indian deal/cashback
offer text (bank T&Cs, coupon SMS, Hinglish WhatsApp forwards) into JSON that **always** passes schema
validation, served by **SGLang** with JSON-schema constrained decoding. Real user: DealFeed (dealfeed.tech).

The core claim we must prove with numbers:
- Constrained decoding alone → ~100% *valid* JSON, but wrong *values*.
- Fine-tuning → correct values. Together → valid **and** accurate, at a fraction of closed-API cost.

## Track rules (non-negotiable — judges check these)
1. **SGLang** is the inference/serving engine for teacher generation, eval and the demo. No vLLM/Ollama in the final path.
2. **CuratorKIT** for data curation (Stage 1), **AlignTune** for fine-tuning (Stage 2), **AuditKIT** for evals (Stage 3).
3. If a Lexsi kit step breaks, keep the kit for the parts that work, document the gap in `docs/EVAL.md` → "Known gaps". Never silently swap it out.

## Read these before coding (in order)
1. `docs/PLAN.md` — hour-by-hour build order with checkpoints. Follow it.
2. `docs/SPEC.md` — schema, API contract, repo layout. Source of truth.
3. `docs/DATA.md`, `docs/TRAINING.md`, `docs/EVAL.md` — per-stage details.
4. `docs/DESIGN.md` — UI rules. **Read fully before writing any frontend code.**
5. `docs/SECURITY.md` — required controls. Every PR-sized change must keep them.

Project skills live in `.claude/skills/`. Load the matching one before each stage:
`sglang-serving`, `curate-offers`, `finetune-aligntune`, `eval-auditkit`, `offerlens-ui`, `security-review`, `ship-demo`.

## Working rules
- **Verify library APIs before using them.** The Lexsi kits are new and change weekly. Check the installed
  version's docs/README (`pip show`, `python -c "import x; help(x)"`, repo notebooks) — never guess kwargs.
  Use Context7 / the docs URLs in the skills when unsure.
- Python 3.11+, managed with `uv`. Type hints everywhere. `ruff` + `mypy --strict` on `src/` must pass.
- Small commits, conventional messages (`feat:`, `fix:`, `chore:`, `docs:`).
- Every script is runnable via `make <target>` and idempotent (re-running doesn't corrupt outputs).
- Config lives in `configs/*.yaml` + env vars via `pydantic-settings`. **No hardcoded paths, ports, or secrets.**
- Pin model **revisions** (commit hashes) in config. `trust_remote_code=False` always.
- **Never fabricate results.** Every number in the UI, README or deck comes from `reports/*.json` produced by `make eval`.
- Long jobs (teacher generation, training) run in the background; write the next stage's code meanwhile.
- When a decision is ambiguous, pick the option that is faster to demo and note it in `docs/DECISIONS.md` (one line each).

## Definition of done
- [ ] `make serve-teacher data train serve-student eval app` all work from a clean clone + `.env`
- [ ] `reports/results.json` has conditions A/B/C (see EVAL.md) with all metrics
- [ ] Demo UI passes the checklist at the bottom of `docs/DESIGN.md`
- [ ] `make check` (ruff, mypy, pytest, bandit, pip-audit, gitleaks) is green
- [ ] README has real numbers, a results chart, and "Known gaps"
