"""Stage 2: LoRA SFT of Qwen2.5-1.5B-Instruct on CuratorKIT's sft_messages with AlignTune.

AlignTune API (verified: inspect.signature(create_sft_trainer)):
  create_sft_trainer(model_name, dataset_name, backend, output_dir, num_epochs, batch_size, learning_rate,
                     max_seq_length, max_samples, system_prompt, config, **kwargs)
Backend is `trl` on Apple Silicon (unsloth needs CUDA). Stop SGLang servers first to free unified memory.
"""

from __future__ import annotations

import json
import time

from offerlens.settings import ROOT, load_config


def main() -> None:
    from aligntune.core.backend_factory import create_sft_trainer

    cfg = load_config("train")
    t0 = time.time()
    trainer = create_sft_trainer(
        model_name=cfg["base_model"],
        dataset_name=str(ROOT / cfg["dataset_dir"]),
        config_name="sft_messages",
        backend=cfg["backend"],
        output_dir=str(ROOT / cfg["output_dir"]),
        task_type="instruction_following",
        dataset_text_field="messages",
        use_peft=True,
        lora_r=cfg["lora_r"],
        lora_alpha=cfg["lora_alpha"],
        lora_dropout=cfg["lora_dropout"],
        lora_target_modules=cfg["target_modules"],
        max_seq_length=cfg["max_seq_length"],
        learning_rate=cfg["learning_rate"],
        warmup_ratio=cfg["warmup_ratio"],
        batch_size=cfg["batch_size"],
        gradient_accumulation_steps=cfg["grad_accum"],
        num_epochs=cfg["epochs"],
        seed=cfg["seed"],
        revision=cfg["base_revision"],
        trust_remote_code=False,
    )
    result = trainer.train()
    log = {"config": cfg, "wall_clock_s": round(time.time() - t0), "result": str(result)}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "train_log.json").write_text(json.dumps(log, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
