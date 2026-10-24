"""Sample ground-truth offer specs in Python (DATA.md §1). The teacher only writes text for them."""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from offerlens.schema import Extraction, Offer

MERCHANTS = [
    "Swiggy", "Zomato", "Amazon", "Flipkart", "Myntra", "BigBasket", "Blinkit", "Zepto", "MakeMyTrip",
    "BookMyShow", "Nykaa", "Ajio", "Croma", "Tata CLiQ", "Uber", "Ola", "IRCTC", "Meesho", "JioMart",
    "Reliance Digital", "Vijay Sales", "Pharmeasy", "1mg", "Netmeds", "Lenskart", "FirstCry", "Pepperfry",
    "Urban Company", "Goibibo", "Cleartrip", "EaseMyTrip", "Yatra", "ixigo", "redBus", "Rapido", "Dunzo",
    "Domino's", "Pizza Hut", "McDonald's", "KFC", "Starbucks", "Licious", "FreshToHome", "Snapdeal",
    "Shoppers Stop", "Lifestyle", "Westside", "Decathlon", "Boat", "Noise", "Mamaearth", "Purplle",
    "Bewakoof", "Zivame", "Tanishq", "CaratLane", "PVR INOX", "Hotstar", "SonyLIV", "Apollo Pharmacy",
]  # fmt: skip
BANKS = [
    "HDFC Bank", "ICICI Bank", "SBI Card", "Axis Bank", "Kotak Mahindra Bank", "IDFC FIRST Bank",
    "AU Small Finance Bank", "OneCard", "American Express", "Yes Bank", "IndusInd Bank", "RBL Bank",
    "Bank of Baroda", "Federal Bank", "HSBC", "Standard Chartered", "Canara Bank", "Punjab National Bank",
]  # fmt: skip
WALLETS = ["Paytm", "PhonePe", "Amazon Pay", "CRED", "Mobikwik", "Google Pay", "Freecharge"]
ISSUERS = BANKS + WALLETS
EXCLUSIONS = [
    "EMI transactions", "Debit cards", "Corporate cards", "Gift card purchases", "Wallet top-ups",
    "Gold and jewellery", "Prepaid cards", "Already discounted items", "International transactions",
    "Cash on delivery orders", "Business accounts", "Alcohol", "Fuel transactions", "Rent payments",
]  # fmt: skip
STYLES = [
    "bank_tnc", "sms", "whatsapp_hinglish", "app_banner", "email_promo", "tweet", "influencer_caption", "noisy_ocr",
]  # fmt: skip
PCT = [5, 7.5, 10, 12, 15, 20, 25, 30, 40, 50]
FLAT = [25, 40, 50, 75, 100, 125, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000]
CAPS = [50, 75, 100, 150, 200, 250, 300, 500, 750, 1000, 1250, 1500, 1750, 2000, 2500, 3000, 5000]
MINS = [99, 149, 199, 249, 299, 399, 499, 599, 799, 999, 1499, 1999, 2499, 2999, 4999, 5000, 7500, 10000]
CODE_WORDS = [
    "FEAST",
    "SAVE",
    "DEAL",
    "FEST",
    "GRAB",
    "MEGA",
    "BIG",
    "HAPPY",
    "DIWALI",
    "NEW",
    "WOW",
    "SUPER",
]


@dataclass
class Spec:
    id: str
    style: str
    reference_date: date
    gold: Extraction
    # Phrasing the teacher must use for some facts, one dict per offer, e.g. {"valid_till": "tomorrow"}.
    phrasing: list[dict[str, str]] = field(default_factory=list)

    def row(self, text: str) -> dict[str, Any]:
        return {
            "id": self.id,
            "style": self.style,
            "reference_date": self.reference_date.isoformat(),
            "text": text,
            "gold": self.gold.model_dump(mode="json"),
        }


def _relative_till(rng: random.Random, ref: date) -> tuple[date, str]:
    choice = rng.choice(["today", "tomorrow", "sunday", "month_end"])
    if choice == "today":
        return ref, rng.choice(["today only", "ends tonight", "aaj raat tak"])
    if choice == "tomorrow":
        return ref + timedelta(days=1), rng.choice(["till tomorrow", "ends tomorrow", "kal tak"])
    if choice == "sunday":
        return ref + timedelta(days=(6 - ref.weekday()) % 7 or 7), "till this Sunday"
    last = calendar.monthrange(ref.year, ref.month)[1]
    return ref.replace(day=last), rng.choice(["till end of the month", "valid till month end"])


def _offer(
    rng: random.Random, ref: date, merchant: str, relative_rate: float
) -> tuple[Offer, dict[str, str]]:
    phrasing: dict[str, str] = {}
    offer_type = rng.choices(
        ["cashback", "instant_discount", "coupon", "bogo", "free_delivery", "reward_points"],
        weights=[30, 30, 20, 5, 7, 8],
    )[0]
    issuer = rng.choice(ISSUERS) if rng.random() < 0.8 or offer_type == "reward_points" else None
    value: float | None = None
    unit: str | None = None
    cap: float | None = None
    if offer_type in ("cashback", "instant_discount", "coupon"):
        if rng.random() < 0.55:
            value, unit = rng.choice(PCT), "percent"
            cap = rng.choice(CAPS) if rng.random() < 0.75 else None
        else:
            value, unit = rng.choice(FLAT), "flat_inr"
    elif offer_type == "reward_points":
        value = rng.choice([2, 3, 5, 10])
        phrasing["value"] = f"{value:g}X reward points"
    min_order: float | None = rng.choice(MINS) if rng.random() < 0.6 else None
    if min_order is not None and value is not None and unit == "flat_inr" and value >= min_order:
        min_order = None
    code = None
    if offer_type == "coupon" or rng.random() < 0.1:
        code = rng.choice(CODE_WORDS) + (
            str(int(value)) if value and value >= 10 else str(rng.randint(10, 99))
        )
    modes: list[str] = []
    if issuer in WALLETS:
        modes = rng.sample(["wallet", "upi"], k=rng.randint(1, 2))
    elif issuer:
        modes = rng.sample(["credit_card", "debit_card", "emi", "netbanking"], k=rng.choice([1, 1, 1, 2]))
    elif rng.random() < 0.2:
        modes = [rng.choice(["upi", "cod", "any"])]
    valid_from = valid_till = None
    if rng.random() < 0.8:
        if rng.random() < relative_rate:
            valid_till, phrasing["valid_till"] = _relative_till(rng, ref)
        else:
            valid_till = ref + timedelta(days=rng.randint(1, 45))
            if rng.random() < 0.3:
                valid_from = ref + timedelta(days=rng.randint(0, (valid_till - ref).days))
    exclusions = rng.sample(EXCLUSIONS, k=rng.choices([0, 1, 2, 3], weights=[55, 25, 15, 5])[0])
    if "debit_card" in modes and "Debit cards" in exclusions:
        exclusions.remove("Debit cards")
    if "emi" in modes and "EMI transactions" in exclusions:
        exclusions.remove("EMI transactions")
    offer = Offer.model_validate(
        {
            "merchant": merchant if rng.random() < 0.92 else None,
            "issuer": issuer,
            "offer_type": offer_type,
            "value": value,
            "value_unit": unit,
            "max_cap_inr": cap,
            "min_order_inr": min_order,
            "coupon_code": code,
            "valid_from": valid_from,
            "valid_till": valid_till,
            "payment_modes": modes,
            "exclusions": exclusions,
            "per_user_limit": rng.choice([1, 1, 2, 3, 5]) if rng.random() < 0.2 else None,
        }
    )
    return offer, phrasing


def sample(seed: int, n: int, cfg: dict[str, Any], prefix: str) -> list[Spec]:
    rng = random.Random(seed)
    lo, hi = (date.fromisoformat(d) for d in cfg["reference_date_range"])
    specs = []
    for i in range(n):
        ref = lo + timedelta(days=rng.randint(0, (hi - lo).days))
        style = rng.choice(STYLES)
        merchant = rng.choice(MERCHANTS)
        roll = rng.random()
        no, multi = cfg["no_offer_rate"], cfg["multi_offer_rate"]
        k = 0 if roll < no else 2 if roll < no + multi else 1
        built = [_offer(rng, ref, merchant, cfg["relative_date_rate"]) for _ in range(k)]
        specs.append(
            Spec(
                id=f"{prefix}-{i:05d}",
                style=style,
                reference_date=ref,
                gold=Extraction(offers=[o for o, _ in built]),
                phrasing=[p for _, p in built],
            )
        )
    return specs
