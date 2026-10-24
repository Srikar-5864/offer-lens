"""Output schema — the single source of truth (SPEC §1)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PaymentMode = Literal["credit_card", "debit_card", "upi", "wallet", "netbanking", "emi", "cod", "any"]
OfferType = Literal[
    "cashback", "instant_discount", "coupon", "bogo", "free_delivery", "reward_points", "other"
]
Exclusion = Annotated[str, Field(max_length=80)]

SCHEMA_PATH = Path(__file__).with_name("schema.json")

SCALAR_FIELDS = (
    "merchant",
    "issuer",
    "offer_type",
    "value",
    "value_unit",
    "max_cap_inr",
    "min_order_inr",
    "coupon_code",
    "valid_from",
    "valid_till",
    "per_user_limit",
)
LIST_FIELDS = ("payment_modes", "exclusions")


class Offer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant: str | None = Field(None, max_length=80)
    issuer: str | None = Field(None, max_length=80)
    offer_type: OfferType
    value: float | None = Field(None, ge=0, le=100000)
    value_unit: Literal["percent", "flat_inr"] | None = None
    max_cap_inr: float | None = Field(None, ge=0, le=10_000_000)
    min_order_inr: float | None = Field(None, ge=0, le=10_000_000)
    coupon_code: str | None = Field(None, pattern=r"^[A-Z0-9_-]{3,20}$")
    valid_from: date | None = None
    valid_till: date | None = None
    payment_modes: list[PaymentMode] = Field(default_factory=list, max_length=8)
    exclusions: list[Exclusion] = Field(default_factory=list, max_length=8)
    per_user_limit: int | None = Field(None, ge=1, le=100)

    @field_validator("coupon_code", mode="before")
    @classmethod
    def _upper_code(cls, v: object) -> object:
        return v.strip().upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _cross_field(self) -> Offer:
        if self.value_unit == "percent" and self.value is not None and self.value > 100:
            raise ValueError("percent value must be <= 100")
        if self.valid_from and self.valid_till and self.valid_from > self.valid_till:
            raise ValueError("valid_from must be <= valid_till")
        return self


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offers: list[Offer] = Field(min_length=0, max_length=4)


def decoding_schema() -> dict[str, Any]:
    """JSON Schema handed to SGLang: every key required so the grammar always emits the full record."""
    schema = Extraction.model_json_schema()
    for definition in schema.get("$defs", {}).values():
        if definition.get("type") == "object":
            definition["required"] = list(definition["properties"])
    schema["required"] = list(schema["properties"])
    return schema


def to_json(extraction: Extraction) -> str:
    """Canonical compact, key-sorted serialisation used for training targets."""
    return json.dumps(
        extraction.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def export() -> None:
    SCHEMA_PATH.write_text(json.dumps(decoding_schema(), indent=2) + "\n")


if __name__ == "__main__":
    export()
