---
name: finetune-aligntune
description: Stage 2 of OfferLens — LoRA SFT of Qwen2.5-1.5B-Instruct on the curated sft_messages data with Lexsi AlignTune (Unsloth backend), then merge for SGLang serving. Use when touching src/offerlens/train or configs/train.yaml.
---

# Fine-tune with AlignTune (Stage 2)

Spec: `docs/TRAINING.md`. Docs: https://aligntune.lexsi.ai · repo: https://github.com/Lexsi-Labs/aligntune

## 0. Verify API first
```bash
pip install aligntune
python -c "import inspect; from aligntune.core.backend_factory import create_sft_trainer as f; print(inspect.signature(f))"
aligntune --help
```
Open the repo's Unsloth SFT example notebook (Qwen2.5-0.5B-Instruct) and mirror its kwargs exactly. Our values come from `configs/train.yaml`.

## 1. Train (`src/offerlens/train/sft.py`)
- Free VRAM: stop the teacher SGLang server.
- Call `create_sft_trainer(..., backend="unsloth", dataset_name="data/curated", config_name="sft_messages", use_peft=True, ...)`.
- Completion-only loss (assistant tokens). Same chat template as inference.
- Run in background: `nohup make train > reports/train.out 2>&1 &`. Tail loss every few minutes; write final metrics to `reports/train_log.json`.
- If unsloth import fails → `backend="trl"`, note in DECISIONS.md.

## 2. Merge (`src/offerlens/train/merge.py`)
- Prefer AlignTune's LoRA merge; fallback `PeftModel.from_pretrained(base, lora).merge_and_unload()`.
- Save safetensors to `models/offerlens-1.5b-merged` with tokenizer. Write `PROVENANCE.json` (base revision, CuratorKIT checksums.txt hash, config hash, git sha, weights SHA-256).

## 3. Smoke test
Serve with `sglang-serving` skill on port 30001; run the 8 demo examples; all must be `valid:true`.

## Watch-outs
- OOM → batch 4, grad_accum 4; or max_seq_length 768.
- Val loss up after epoch 1 → use epoch-1 checkpoint.
- Never train on `data/real/` or the seed-7 synthetic test.
