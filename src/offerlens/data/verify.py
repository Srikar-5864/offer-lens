"""Deterministic verification gate: does the teacher's text state every gold fact, and nothing extra?

Replaces DATA.md's teacher round-trip check (see DECISIONS.md): the 7B-4bit teacher's own extraction was the
noisier side of that comparison, so it rejected good text. Checking surface forms against the spec is exact.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from offerlens.data.seeds import ISSUERS, MERCHANTS
from offerlens.schema import Extraction

ISSUER_ALIASES = {
    "American Express": ["american express", "amex"],
    "AU Small Finance Bank": ["au small finance", "au bank", "au "],
    "IDFC FIRST Bank": ["idfc"],
    "Punjab National Bank": ["punjab national", "pnb"],
    "Bank of Baroda": ["baroda", "bob "],
    "Standard Chartered": ["standard chartered", "stanchart", "sc bank"],
    "Kotak Mahindra Bank": ["kotak"],
    "Amazon Pay": ["amazon pay"],
    "Google Pay": ["google pay", "gpay"],
    "SBI Card": ["sbi"],
}
MODE_WORDS = {
    "credit_card": r"credit|\bcc\b",
    "debit_card": r"debit|\bdc\b",
    "emi": r"\bemi",
    "netbanking": r"net\s?-?banking",
    "upi": r"\bupi",
    "wallet": r"wallet",
    "cod": r"\bcod\b|cash on delivery",
    "any": r".",
}
TYPE_WORDS = {
    "bogo": r"buy\s?(1|one)|bogo|b1g1|1\s?\+\s?1",
    "free_delivery": r"free\s(home\s)?(delivery|shipping)|delivery\s(is\s)?free|zero delivery",
    "reward_points": r"reward|points|\brp\b",
    "cashback": r"cash\s?-?back|back\b",
    "instant_discount": r"off\b|discount|save",
    "coupon": r".",
}
OFFER_WORDS = r"%|cash\s?-?back|coupon|promo code|discount|\boff\b"
RELATIVE_WORDS = {
    "tomorrow": r"tomorrow|\bkal\b",
    "kal": r"tomorrow|\bkal\b",
    "today": r"today|tonight|\baaj\b",
    "tonight": r"today|tonight|\baaj\b",
    "aaj": r"today|tonight|\baaj\b",
    "sunday": r"sunday",
    "month": r"month",
}
_OCR_DIGITS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5"})


def _squash(s: str) -> str:
    s = s.casefold().translate(str.maketrans({"0": "o", "1": "l", "i": "l", "5": "s"}))
    return re.sub(r"[^a-z0-9]", "", s)


def _numbers_text(text: str) -> str:
    # O/l/I next to digits are OCR noise for 0/1; drop thousands separators.
    prev, t = "", text
    while prev != t:  # fixed point: "3OO" -> "30O" -> "300"
        prev, t = t, re.sub(r"(?<=\d)[OolIS]|[OolIS](?=\d)", lambda m: m.group().translate(_OCR_DIGITS), t)
    return re.sub(r"(?<=\d),(?=\d)", "", t)


def _has_number(ntext: str, value: float) -> bool:
    forms = {f"{value:g}"}
    if value >= 1000:
        forms |= {f"{value / 1000:g}k", f"{value / 1000:g} k"}
    return any(re.search(rf"(?<![\d.]){re.escape(f)}(?![\d])", ntext, re.I) for f in forms)


def _has_date(text: str, d: date) -> bool:
    low = text.casefold()
    mon = d.strftime("%b").casefold()
    if re.search(rf"(?<!\d){d.day}(st|nd|rd|th)?\s*(of\s*)?{mon}", low) or re.search(
        rf"{mon}\w*\s*{d.day}(?!\d)", low
    ):
        return True
    return bool(re.search(rf"(?<!\d)0?{d.day}\s*[/\-.]\s*0?{d.month}(?!\d)", low))


def _has_relative(text: str, phrase: str) -> bool:
    low = text.casefold()
    return any(re.search(rx, low) for key, rx in RELATIVE_WORDS.items() if key in phrase.casefold())


def _issuer_ok(text: str, issuer: str) -> bool:
    low = text.casefold()
    aliases = ISSUER_ALIASES.get(issuer, [issuer.split()[0].casefold()])
    return any(a in low for a in aliases) or _squash(issuer.split()[0]) in _squash(text)


def problems(text: str, gold: Extraction, phrasing: list[dict[str, str]]) -> list[str]:
    """Empty list = text faithfully carries the spec."""
    out: list[str] = []
    low, ntext, sq = text.casefold(), _numbers_text(text), _squash(text)
    if len(text) > 700 or re.search(r"(.{2,8}?)\1{4,}", text):
        return ["degenerate repetition"]
    named = {o.merchant for o in gold.offers} | {o.issuer for o in gold.offers}
    for brand in MERCHANTS + ISSUERS:
        if any(brand in n for n in named if n):  # "Amazon" inside "Amazon Pay"
            continue
        # Case-sensitive: "Noise"/"Boat" are also plain words.
        if re.search(rf"\b({re.escape(brand)}|{re.escape(brand.upper())})\b", text):
            out.append(f"foreign brand {brand}")
    if not gold.offers:
        return ["offer-like wording in no-offer text"] if re.search(OFFER_WORDS, low) else []
    allowed: set[float] = set()
    for k, (offer, ph) in enumerate(zip(gold.offers, phrasing, strict=True)):
        o: dict[str, Any] = offer.model_dump()
        if o["merchant"] and _squash(o["merchant"]) not in sq:
            out.append(f"{k}.merchant")
        if o["issuer"] and not _issuer_ok(text, o["issuer"]):
            out.append(f"{k}.issuer")
        for f in ("value", "max_cap_inr", "min_order_inr", "per_user_limit"):
            if o[f] is not None:
                allowed.add(float(o[f]))
                if not _has_number(ntext, float(o[f])):
                    out.append(f"{k}.{f}")
        if o["coupon_code"] and _squash(o["coupon_code"]) not in sq:
            out.append(f"{k}.coupon_code")
        if not re.search(TYPE_WORDS[o["offer_type"]], low):
            out.append(f"{k}.offer_type")
        for f in ("valid_from", "valid_till"):
            d = o[f]
            if d is None:
                continue
            allowed |= {float(d.day), float(d.month), float(d.year), float(d.year % 100)}
            ok = _has_relative(text, ph[f]) if f in ph else _has_date(text, d)
            if not ok:
                out.append(f"{k}.{f}")
        for m in o["payment_modes"]:
            if not re.search(MODE_WORDS[m], low):
                out.append(f"{k}.payment_modes:{m}")
        for ex in o["exclusions"]:
            stem = ex.split()[0].casefold().rstrip("s")
            stem = {"cash": "cash on delivery|cod", "international": "international|int'l|intl"}.get(
                stem, stem
            )
            if not re.search(stem, low):
                out.append(f"{k}.exclusions:{ex}")
    # Writer hallucinations: any number >= 10 the spec doesn't explain (hashtag/handle digits excluded).
    for tok in re.findall(r"(?<![#@\w.])(\d+(?:\.\d+)?)(k?)(?![\w])", ntext, re.I):
        n = float(tok[0]) * (1000 if tok[1] else 1)
        if n >= 10 and n not in allowed:
            out.append(f"extra number {tok[0]}{tok[1]}")
    return out
