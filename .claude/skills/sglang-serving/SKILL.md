---
name: sglang-serving
description: Launch, health-check and call SGLang servers (teacher, base, fine-tuned student) with JSON-schema constrained decoding for OfferLens. Use before any model serving, generation or eval call.
---

# SGLang serving for OfferLens

Docs: https://docs.sglang.io/ · repo: https://github.com/sgl-project/sglang
Verify flags against the installed version: `python -m sglang.launch_server --help`.

## Ports (from configs/models.yaml, never hardcode)
| Role | Model | Port |
|---|---|---|
| teacher | Qwen2.5-7B/14B-Instruct (pick by VRAM, see PLAN H0) | 30000 |
| base | Qwen2.5-1.5B-Instruct | 30002 |
| student | models/offerlens-1.5b-merged | 30001 |

## Launch (Makefile targets wrap these)
```bash
python -m sglang.launch_server --model-path "$MODEL" --revision "$REV" \
  --host 127.0.0.1 --port "$PORT" --mem-fraction-static 0.35 --served-model-name "$NAME"
```
- **Always `--host 127.0.0.1`.** Never 0.0.0.0 (SECURITY.md §1).
- Several servers on one GPU: lower `--mem-fraction-static` per server so they fit (e.g. teacher 0.55 during data gen, then stop it).
- Stop the teacher before training to free VRAM.
- Wait for readiness: poll `GET http://127.0.0.1:$PORT/health` until 200 (timeout 300s).

## Constrained decoding (OpenAI-compatible)
```python
from openai import OpenAI
import json, pathlib
schema = json.loads(pathlib.Path("src/offerlens/schema.json").read_text())
client = OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key=settings.sglang_api_key or "none")
resp = client.chat.completions.create(
    model=name, temperature=0, max_tokens=512, timeout=10,
    messages=prompt.messages(text, reference_date),
    response_format={"type": "json_schema",
                     "json_schema": {"name": "offer_extraction", "schema": schema}},
)
```
- Condition A (unconstrained) = same call without `response_format`; parse the first JSON object from the text.
- Always re-validate with `Extraction.model_validate_json` — constraint guarantees shape, Pydantic enforces our validators.
- If a schema feature isn't supported by the grammar backend (check server logs), simplify the exported schema
  (e.g. drop `format: date`, keep a regex pattern `^\d{4}-\d{2}-\d{2}$`) — keep Pydantic as the strict check.

## Throughput measurement
Use asyncio + `httpx.AsyncClient` with a semaphore of 16; warm up with 10 requests first; report p50/p95 and rps.

## Put all of this in `src/offerlens/sglang_client.py`
One sync + one async client function, retries (2, exponential), timeouts, and structured logging (hash of input, no raw text).
