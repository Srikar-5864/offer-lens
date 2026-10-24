# Decisions log
One line per decision: `HH:MM — decision — why — revisit?`

- 00:00 — Student = Qwen2.5-1.5B-Instruct — strong JSON prior, trains in <40 min — no
- 00:00 — Merged LoRA served on separate SGLang port — simpler than runtime LoRA — no
- 00:00 — Frontend = FastAPI static + vanilla JS — no build step, strict CSP friendly — no
- 21:55 — Hardware is an Apple M4, 16 GB unified memory, no NVIDIA GPU — that's the machine we have — no
- 21:58 — SGLang built from source (commit 059ba6b) with the MLX backend (`SGLANG_USE_MLX=1`), in its own venv at ~/code/sglang/.venv — PyPI sglang needs CUDA kernels; docs.sglang.io apple_metal page — no
- 22:05 — `--mlx-enable-sampling` is mandatory: without it SGLang's MLX path silently skips xgrammar vocab masks and json_schema output is NOT constrained (we saw `"Flat Rs"` returned) — found by reading hardware_backend/mlx/tp_worker.py — no
- 22:08 — Teacher = mlx-community/Qwen2.5-7B-Instruct-4bit @ c26a38f — bf16 7B doesn't fit next to anything else in 16 GB — revisit on a GPU box (PLAN: 7B/14B bf16)
- 22:10 — Base pinned to Qwen/Qwen2.5-1.5B-Instruct @ 989aa79 — reproducibility — no
- 22:12 — AlignTune backend = `trl` (pinned aligntune 0.1.17 + torchao<0.14) — unsloth needs CUDA; aligntune 0.1.28 requires torch<=2.10 + vllm (no macOS wheels); torchao 0.18 breaks aligntune's TRL import (`ScalingType`) — revisit on GPU
- 22:16 — CuratorKIT `clean_transforms={"strip_html": False}` — the default cleaner deleted our `<offer_text>` delimiters, so training prompts would not match inference; curate.py asserts the prompt contract on every exported row — no
- 22:22 — Data verification gate = deterministic fact-presence check (data/verify.py) instead of DATA.md's teacher round-trip — in the smoke run the 7B-4bit teacher's own extraction (relative dates, offer_type, exclusion wording) was the noisy side, rejecting 30/32 good-or-fixable rows; the surface check is exact and halves teacher calls. CuratorKIT's LLM reward judge stays as the second, model-based gate — no
- 22:24 — Writer prompt uses plain-language fact labels ("maximum discount cap in rupees") instead of JSON keys; style hints no longer name a real brand — pass rate went 31% → 67% — no
- 22:30 — Teacher capped at 16 concurrent requests, `--mem-fraction-static 0.40` — 32 concurrent OOM'd Metal; 0.55 pushed the machine into swap (throughput 55 → 18 tok/s) — no
- 22:40 — Stopped the pipeline run at the user's request (laptop lagging under the 7B teacher); stages 1–3 are implemented but not executed end to end. No numbers are reported anywhere until `make eval` produces them — yes, run on a GPU box
- 22:45 — Eval runner = AuditKIT `evaluate()` with our SGLang client as the `list[str] -> list[str]` model callable and our metrics as `@ak.scorer`s — AuditKIT's OpenAI adapter can't pass `response_format` — no
