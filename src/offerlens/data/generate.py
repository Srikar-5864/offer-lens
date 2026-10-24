"""Stage 1a: teacher (SGLang) writes messy offer text for each Python-sampled spec, then a verification gate.

Outputs (resumable — rows already written are skipped on re-run):
  data/raw/offers.jsonl   train pool (seed 42)   {id, style, reference_date, text, gold, problems}
  data/raw/test.jsonl     synthetic test (seed 7, separate seed = no leakage)
  data/raw/flagged.jsonl  rows that failed the round-trip gate
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from offerlens import sglang_client
from offerlens.data.seeds import Spec, sample
from offerlens.data.verify import problems
from offerlens.settings import ROOT, load_config

STYLE_GUIDE = {
    "bank_tnc": "formal bank terms-and-conditions legalese, one dense paragraph, 'Offer valid…', 'T&C apply'",
    "sms": "a promotional SMS: the merchant's name in CAPS as a prefix, abbreviations, mixes Rs/Rs./INR/₹, "
    "under 200 chars",
    "whatsapp_hinglish": "a WhatsApp forward in Hinglish (Hindi words in Latin script mixed with English), emojis, "
    "casual tone like 'bhai', 'mil raha', 'jaldi karo'",
    "app_banner": "a terse app banner: fragments separated by '·' or '|', no full sentences",
    "email_promo": "a marketing email snippet with a subject line and 2-3 short lines",
    "tweet": "a tweet from the brand's handle with hashtags",
    "influencer_caption": "an Instagram influencer caption, chatty, emojis, 'link in bio' vibe",
    "noisy_ocr": "OCR of a poster: some letters swapped for look-alike digits (O→0, l→1, I→1), broken spacing, "
    "a few typos, but every number still readable",
}

WRITER_SYSTEM = (
    "You write realistic Indian shopping offer messages. Include every fact you are given, exactly once, and "
    "nothing else: no extra numbers, dates, codes, conditions, other brands, banks or payment methods. Facts "
    "marked 'do not mention' must not appear. Output only the message text."
)
NOISE_TOPICS = ["order delivered", "OTP-free login reminder", "app update notice", "rate your ride",
                "account statement ready", "newsletter with no discount", "delivery delayed apology"]  # fmt: skip
LABELS = {
    "merchant": "store / brand (the ONLY brand to name)",
    "issuer": "bank, card or wallet (the ONLY one to name)",
    "offer_type": "kind of offer",
    "value": "offer amount",
    "max_cap_inr": "maximum discount/cashback cap in rupees",
    "min_order_inr": "minimum order / transaction value in rupees",
    "coupon_code": "coupon code (write it exactly)",
    "valid_from": "offer starts on",
    "valid_till": "offer ends on",
    "payment_modes": "payment methods it works with",
    "exclusions": "not valid on",
    "per_user_limit": "max times one user can use it",
}
TYPE_TEXT = {
    "cashback": "cashback", "instant_discount": "instant discount / off", "coupon": "coupon discount",
    "bogo": "buy one get one free", "free_delivery": "free delivery", "reward_points": "reward points",
}  # fmt: skip


def _fact_lines(offer: dict[str, Any], phrasing: dict[str, str]) -> list[str]:
    lines = []
    for key, label in LABELS.items():
        val = offer[key]
        if key in phrasing:
            lines.append(f'- {label}: say it as "{phrasing[key]}"')
        elif val in (None, []):
            if key in (
                "max_cap_inr",
                "min_order_inr",
                "coupon_code",
                "valid_till",
                "issuer",
                "per_user_limit",
            ):
                lines.append(f"- {label}: do not mention")
        elif key == "value":
            unit = offer["value_unit"]
            lines.append(f"- {label}: " + (f"{val:g}%" if unit == "percent" else f"₹{val:g} flat"))
        elif key == "offer_type":
            lines.append(f"- {label}: {TYPE_TEXT[val]}")
        elif key == "payment_modes":
            lines.append(f"- {label}: {', '.join(m.replace('_', ' ') for m in val)}")
        elif key in ("valid_from", "valid_till"):
            lines.append(f"- {label}: {date.fromisoformat(val):%d %B %Y}")
        else:
            lines.append(f"- {label}: {', '.join(val) if isinstance(val, list) else val}")
    return lines


def writer_messages(spec: Spec) -> list[dict[str, str]]:
    style = STYLE_GUIDE[spec.style]
    if not spec.gold.offers:
        topic = NOISE_TOPICS[int(spec.id.rsplit("-", 1)[1]) % len(NOISE_TOPICS)]
        user = f"Write {style}. It must contain NO offer, discount, cashback or coupon. Topic: {topic}."
    else:
        blocks = []
        for i, (offer, ph) in enumerate(zip(spec.gold.offers, spec.phrasing, strict=True), 1):
            facts = "\n".join(_fact_lines(offer.model_dump(mode="json"), ph))
            blocks.append(f"Offer {i}:\n{facts}")
        user = (
            f"Style: {style}.\nToday is {spec.reference_date:%A %d %B %Y}. Write dates naturally "
            f"(e.g. '31st Oct', '31/10'), not ISO.\n" + "\n\n".join(blocks)
        )
    return [{"role": "system", "content": WRITER_SYSTEM}, {"role": "user", "content": user}]


async def _one(
    client: httpx.AsyncClient, spec: Spec, temperature: float, gate: int
) -> tuple[dict[str, Any], bool]:
    body = sglang_client.payload(
        "teacher", writer_messages(spec), constrained=False, temperature=temperature, max_tokens=200
    ) | {"top_p": 0.95, "frequency_penalty": 0.3}
    for _attempt in range(2):  # one retry with a fresh sample
        text = (await sglang_client.achat(client, "teacher", body, timeout=300)).strip().strip('"')
        issues = problems(text, spec.gold, spec.phrasing)
        if len(issues) <= gate:
            break
    return spec.row(text) | {"problems": issues}, len(issues) <= gate


def _done_ids(*paths: Path) -> set[str]:
    return {
        json.loads(line)["id"] for p in paths if p.exists() for line in p.read_text().splitlines() if line
    }


async def run(specs: list[Spec], out: Path, flagged: Path, cfg: dict[str, Any]) -> None:
    todo = [s for s in specs if s.id not in _done_ids(out, flagged)]
    print(f"{out.name}: {len(specs) - len(todo)} done, {len(todo)} to generate")
    sem = asyncio.Semaphore(cfg["concurrency"])
    kept = dropped = 0

    async with httpx.AsyncClient() as client:

        async def guarded(spec: Spec) -> None:
            nonlocal kept, dropped
            async with sem:
                try:
                    row, ok = await _one(client, spec, cfg["teacher_temperature"], cfg["max_problems"])
                except httpx.HTTPError as exc:
                    print(f"skip {spec.id}: {type(exc).__name__}")
                    return
            with (out if ok else flagged).open("a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            kept, dropped = kept + ok, dropped + (not ok)
            if (kept + dropped) % 50 == 0:
                print(f"  {kept + dropped}/{len(todo)} kept={kept} flagged={dropped}", flush=True)

        await asyncio.gather(*(guarded(s) for s in todo))
    print(f"{out.name}: kept={kept} flagged={dropped}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="cap specs per split (smoke runs)")
    args = ap.parse_args()
    cfg = load_config("data")
    raw = ROOT / cfg["raw_dir"]
    raw.mkdir(parents=True, exist_ok=True)
    n_train, n_test = cfg["n_train_specs"], cfg["n_test_specs"]
    if args.limit:
        n_train, n_test = min(n_train, args.limit), min(n_test, args.limit)
    test = sample(cfg["seed_test"], n_test, cfg, "test")
    train = sample(cfg["seed_train"], n_train, cfg, "train")
    asyncio.run(run(test, raw / "test.jsonl", raw / "test_flagged.jsonl", cfg))
    asyncio.run(run(train, raw / "offers.jsonl", raw / "flagged.jsonl", cfg))


if __name__ == "__main__":
    main()
