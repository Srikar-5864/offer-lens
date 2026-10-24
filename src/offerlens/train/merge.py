"""Merge the LoRA into the base model (safetensors only) and write PROVENANCE.json for SGLang serving."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from offerlens.eval.run import git_sha
from offerlens.settings import ROOT, load_config


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cfg = load_config("train")
    out = ROOT / cfg["merged_dir"]
    kw = {"revision": cfg["base_revision"], "trust_remote_code": False}
    base = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"], torch_dtype=torch.bfloat16, use_safetensors=True, **kw
    )
    merged = PeftModel.from_pretrained(base, str(ROOT / cfg["output_dir"])).merge_and_unload()
    merged.save_pretrained(out, safe_serialization=True)
    AutoTokenizer.from_pretrained(cfg["base_model"], **kw).save_pretrained(out)
    checksums = ROOT / load_config("data")["curated_dir"] / "checksums.txt"
    provenance = {
        "base_model": cfg["base_model"],
        "base_revision": cfg["base_revision"],
        "data_checksums_sha256": _sha256(checksums) if checksums.exists() else None,
        "train_config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
        "git_sha": git_sha(),
        "weights_sha256": {p.name: _sha256(p) for p in sorted(out.glob("*.safetensors"))},
    }
    (out / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"merged -> {out}")


if __name__ == "__main__":
    main()
