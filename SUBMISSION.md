# OfferLens — submission answers

## The problem it solves
* **Turns messy Indian deal text into clean, structured data.** Bank T&Cs, coupon SMSes and Hinglish WhatsApp forwards ("Bhai Myntra pe Axis card se 15% cashback… kal raat tak") become one JSON record: merchant, bank/wallet, cashback %, cap, minimum order, coupon code, validity dates, payment modes and exclusions.
* **Output is guaranteed to be valid.** SGLang's JSON-schema constrained decoding means the model can only emit schema-shaped JSON, and every result is re-checked with Pydantic, so a deals app like DealFeed can put it straight into its database without a fallback parser.
* **Runs locally on a small open model (1.5B).** No per-message bill from a closed API, and offer text (which can include user SMSes) never leaves the machine.
* **Safer against prompt injection.** Offer text is treated as untrusted data; because decoding is grammar-constrained, an "ignore previous instructions…" message still yields only an offer record, never prose, HTML or a leaked system prompt.
* **Every value is traceable.** The demo UI underlines the exact span in the source text that each extracted field came from, and shows "—" instead of guessing when a field isn't stated, so a reviewer can verify a deal at a glance.

## Challenges we ran into
* **No NVIDIA GPU, so SGLang wouldn't install.** The PyPI wheel needs CUDA kernels. We built SGLang from source with its Apple Silicon MLX backend and ran it in its own virtual environment.
* **JSON-schema constraints were silently ignored on Apple Silicon.** The first "constrained" call returned plain text (`Flat Rs`). By reading SGLang's MLX worker source we found that grammar masks are only applied when `--mlx-enable-sampling` is set. With it on, output became valid JSON. That also showed our thesis early: it was valid but had a wrong date (`"3990-01-31"`).
* **CuratorKIT's text cleaner broke our prompt contract.** Its default HTML stripper deleted the `<offer_text>` delimiters from training rows, so training prompts would not have matched inference prompts. We turned off `strip_html` and added an assertion that checks the exact prompt on every exported row.
* **The teacher-model verification gate rejected good data.** In the round-trip check (the teacher extracts from its own text), the 4-bit 7B teacher's own mistakes on relative dates and wording caused about 94% of rows to be rejected. We replaced it with a deterministic fact-presence gate: every gold value must appear in the text, and no unexplained numbers or other brands are allowed. CuratorKIT's LLM judge stays as the second gate. Rewriting the writer prompt in plain language raised the pass rate from 31% to 67%.
* **Memory pressure on a 16 GB laptop.** Running 32 concurrent requests on the 7B teacher crashed Metal with out-of-memory, and a 55% KV reservation pushed the machine into swap (throughput fell from 55 to 18 tokens/s). We capped requests at 16 and lowered the memory fraction. In the end we paused the full data run, because the laptop needs to stay usable. That is documented under Known gaps.
* **Dependency conflicts in the Lexsi kits.** The latest AlignTune needs vLLM (no macOS wheels), and a newer torchao broke AlignTune's TRL backend import (`ScalingType`). We pinned AlignTune 0.1.17 with `torchao<0.14` and used the `trl` backend instead of unsloth.

## Tracks applied
Local LLM Track — Problem Statement #5: Structured output and extraction

## Technologies used
Python 3.12, SGLang (MLX backend, xgrammar JSON-schema constrained decoding), Qwen2.5-1.5B-Instruct (student), Qwen2.5-7B-Instruct 4-bit (teacher), Lexsi CuratorKIT (MinHash dedup, secrets gate, LLM judge), Lexsi AlignTune (LoRA SFT, TRL backend), Lexsi AuditKIT (evaluation runner with custom scorers), MLX, PyTorch, PEFT, Pydantic v2, FastAPI, slowapi, httpx, vanilla HTML/CSS/JS (no build step, strict CSP), uv, ruff, mypy

## Platforms
macOS on Apple Silicon (built and run on an M4 with 16 GB), web browser (desktop and mobile, light and dark), Linux with an NVIDIA GPU (the standard SGLang/unsloth path, configured but not run)
