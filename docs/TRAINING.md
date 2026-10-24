# Stage 2 — Fine-tuning (AlignTune)

Docs: https://aligntune.lexsi.ai · repo: https://github.com/Lexsi-Labs/aligntune · `pip install aligntune`

## Config (`configs/train.yaml`)
| Key | Value | Why |
|---|---|---|
| base model | `Qwen/Qwen2.5-1.5B-Instruct` (pin revision) | strong JSON prior, fast, fits any GPU |
| backend | `unsloth` (fallback `trl`) | faster; AlignTune routes both |
| method | SFT + LoRA | |
| lora_r / alpha / dropout | 16 / 32 / 0.05 | |
| target modules | all linear (q,k,v,o,gate,up,down) | |
| epochs | 2 | 1 if behind schedule |
| lr / warmup | 2e-4 / 0.05 | |
| max_seq_length | 1024 | offers are short |
| batch / grad_accum | 8 / 2 (adjust to VRAM) | |
| loss | assistant tokens only (completion-only) | don't train on the prompt |
| seed | 42 | reproducibility |

## Expected API shape (verify against installed version before use)
```python
from aligntune.core.backend_factory import create_sft_trainer
trainer = create_sft_trainer(
    model_name="Qwen/Qwen2.5-1.5B-Instruct",
    dataset_name="data/curated",          # CuratorKIT output folder
    config_name="sft_messages",
    backend="unsloth",
    output_dir="models/offerlens-lora",
    task_type="instruction_following",
    use_peft=True, lora_r=16, lora_alpha=32,
    max_seq_length=1024, dataset_text_field="messages",
    learning_rate=2e-4, batch_size=8, gradient_accumulation_steps=2, num_epochs=2,
)
trainer.train()
```
Kwarg names differ across versions — open the installed package's docs/notebooks first (skill `finetune-aligntune`).

## Merge & serve
Merge LoRA into base (AlignTune's LoRA merge, or `peft` `merge_and_unload()`), save safetensors to
`models/offerlens-1.5b-merged`, then serve with SGLang on port 30001. Merged serving is simpler and faster
than runtime LoRA for the demo. Write `models/offerlens-1.5b-merged/PROVENANCE.json`
(base revision, data checksum from CuratorKIT, config hash, git sha).

## Watch-outs
- Chat template: use the tokenizer's own template for both training and inference.
- Don't put the JSON schema in the prompt during training if you won't at inference (keep prompt identical).
- Overfitting signal: val loss rising after epoch 1 → take the epoch-1 checkpoint.
