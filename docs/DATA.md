# Stage 1 — Data (CuratorKIT + SGLang teacher)

## Goal
~1,500 curated train rows, 150 val, 200 synthetic test, 30 **real** test (hand-labelled, never trained on).

## Generation design (diversity is the point)
Sample a structured "offer spec" first in Python (ground truth), then ask the teacher to **write** messy text
for it. This gives us gold labels for free and avoids asking the teacher to extract (which would copy its errors).

1. `seeds.py` — random spec: merchant (60: Swiggy, Zomato, Amazon, Flipkart, Myntra, BigBasket, Blinkit, Zepto,
   MakeMyTrip, BookMyShow, Nykaa, Ajio, Croma, Tata CLiQ, Uber, Ola, IRCTC, …), issuer (25 banks/cards/wallets:
   HDFC, ICICI, SBI Card, Axis, Kotak, IDFC FIRST, AU, OneCard, Amex, Paytm, PhonePe, Amazon Pay, CRED, Mobikwik…),
   offer_type, value/unit, caps, min order, code, dates (absolute AND relative to a reference_date), payment modes,
   0–3 exclusions, 10% of specs have 2 offers, 5% have **no offer** (noise text → `offers: []`).
2. Style templates (pick one per sample): `bank_tnc` (formal legalese) · `sms` (abbrevs, caps, ₹/Rs/INR mixed) ·
   `whatsapp_hinglish` (code-mixed, emojis) · `app_banner` (terse) · `email_promo` · `tweet` ·
   `influencer_caption` · `noisy_ocr` (typos, broken spacing).
3. `generate.py` — SGLang teacher writes text from spec + style. Temperature 0.9. Then a **round-trip check**:
   teacher extracts from its own text with constrained decoding; if it disagrees with the spec on >1 field,
   flag the sample (the text likely dropped/changed info). This is our verification gate.

## Curation with CuratorKIT (`curate.py`)
Docs: https://curatorkit.lexsi.ai/latest/ · repo: https://github.com/Lexsi-Labs/CuratorKIT
Install: `pip install "curatorkit[all]"` (Python ≥3.11). Point its LLM at SGLang via LiteLLM's OpenAI route:
`llm_model="openai/<served-model-name>"`, `llm_api_base="http://127.0.0.1:30000/v1"`.
Stages to use (verify names against installed version):
- `clean=True`, `dedup="minhash"` (near-duplicate offers are the #1 failure of synthetic data here)
- hygiene gate (secrets/PII) — run especially on the **real** DealFeed offers before anything touches disk outside `data/real/`
- judge/reward gate with `judge_llm_model` = teacher, `reward_threshold≈0.7`, `judge_on_error="reject"`
- `export_formats=["messages"]` → `sft_messages.jsonl`; `output_split={"train":0.9,"validation":0.1}`
- Keep `manifest.json`, `rejected.jsonl`, `dataset_card.md`, `checksums.txt` — show rejection breakdown in the deck.

Row format (chat messages): system = prompt.SYSTEM, user = prompt.render(text, reference_date),
assistant = `Extraction(...).model_dump_json()` (compact, sorted keys).

## Real test set (the credibility anchor)
30 real offers from DealFeed sources, labelled by hand into `data/real/real_test.jsonl`. Gitignored.
Strip phone numbers, names, referral links, and tracking URLs before saving. Never used for training or prompt tuning.

## Stretch (only if ahead): curated vs raw ablation
Train a second LoRA on raw (uncurated) data, eval both — directly shows CuratorKIT's value (PS #8 flavour).
