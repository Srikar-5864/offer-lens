# How to start

1. Unzip on the GPU machine, `cd offerlens`, `git init`.
2. `cp .env.example .env` and fill it (HF token, pinned revisions, GPU ₹/hour).
3. Open Claude Code in this folder and paste the prompt below.

---

```
Read CLAUDE.md, then docs/PLAN.md and docs/SPEC.md. We are at H0 of the plan.
Create a task list from PLAN.md (one task per checkpoint) and start H0:
check the GPU, scaffold the repo layout from SPEC §4 with pyproject (uv), Makefile targets from SPEC §5,
settings.py with pydantic-settings, schema.py + schema.json + tests, and pre-commit.
Then smoke-test SGLang and each Lexsi kit using the sglang-serving, curate-offers,
finetune-aligntune and eval-auditkit skills (step 0 "verify API" in each).
Record real API signatures and the GPU in docs/DECISIONS.md. Stop and show me H0 results before H1.
```

After each checkpoint, say: `Continue to the next stage of PLAN.md.`
Before the UI: `Load the offerlens-ui skill and build the frontend exactly to docs/DESIGN.md.`
Before demo: `Run the security-review skill, then the ship-demo skill.`

## Crew split (if 3–4 people)
| Person | Owns | Starts at |
|---|---|---|
| A | SGLang + data gen + CuratorKIT | H0 |
| B | Labels 30 real DealFeed offers, then AlignTune training | H0 (labelling), H2 |
| C | Metrics + AuditKIT eval + report | H1 (metrics w/ tests) |
| D | UI + API + security + deck numbers | H1 (UI shell on mocked API) |
