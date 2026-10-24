"""Extraction metrics (EVAL.md). Pure functions; an invalid prediction is scored as an empty extraction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import permutations
from statistics import mean
from typing import Any

from offerlens.schema import LIST_FIELDS, SCALAR_FIELDS, Extraction

OfferDict = dict[str, Any]
_EMPTY: OfferDict = {f: None for f in SCALAR_FIELDS} | {f: [] for f in LIST_FIELDS}
_FUZZY = 0.8


def _norm(v: Any) -> Any:
    return v.strip().casefold() if isinstance(v, str) else v


def scalar_eq(gold: Any, pred: Any) -> bool:
    if gold is None or pred is None:
        return gold is None and pred is None
    if isinstance(gold, int | float) and isinstance(pred, int | float):
        return abs(float(gold) - float(pred)) <= 0.5
    return bool(_norm(gold) == _norm(pred))


def _fuzzy(a: str, b: str) -> bool:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= _FUZZY


def list_counts(gold: Sequence[str], pred: Sequence[str], fuzzy: bool) -> tuple[int, int, int]:
    """(tp, fp, fn) with greedy one-to-one matching."""
    remaining = list(pred)
    tp = 0
    for g in gold:
        hit = next((p for p in remaining if (_fuzzy(g, p) if fuzzy else _norm(g) == _norm(p))), None)
        if hit is not None:
            remaining.remove(hit)
            tp += 1
    return tp, len(remaining), len(gold) - tp


def _overlap(g: OfferDict, p: OfferDict) -> int:
    return sum(g[f] is not None and scalar_eq(g[f], p[f]) for f in SCALAR_FIELDS)


def align(gold: list[OfferDict], pred: list[OfferDict]) -> list[tuple[OfferDict, OfferDict]]:
    """Best one-to-one pairing on field overlap (brute force is fine: <=4 offers), padding with empty offers."""
    n = max(len(gold), len(pred))
    g = gold + [_EMPTY] * (n - len(gold))
    p = pred + [_EMPTY] * (n - len(pred))
    best = max(permutations(range(n)), key=lambda perm: sum(_overlap(g[i], p[j]) for i, j in enumerate(perm)))
    return [(g[i], p[j]) for i, j in enumerate(best)]


def offers(e: Extraction | None) -> list[OfferDict]:
    return [o.model_dump(mode="json") for o in e.offers] if e else []


@dataclass
class SampleScore:
    valid: bool
    offer_count_ok: bool
    field_acc: float = 1.0
    exact: bool = False
    failing_fields: list[str] = field(default_factory=list)
    tp: int = 0
    fp: int = 0
    fn: int = 0
    halluc: int = 0
    halluc_den: int = 0
    omit: int = 0
    omit_den: int = 0


def score(gold: Extraction, pred: Extraction | None) -> SampleScore:
    s = SampleScore(
        valid=pred is not None, offer_count_ok=len(gold.offers) == len(pred.offers if pred else [])
    )
    hits = total = 0
    for k, (g, p) in enumerate(align(offers(gold), offers(pred))):
        for f in SCALAR_FIELDS:
            ok = scalar_eq(g[f], p[f])
            hits += ok
            total += 1
            if not ok:
                s.failing_fields.append(f"{k}.{f}")
        for f in LIST_FIELDS:
            tp, fp, fn = list_counts(g[f], p[f], fuzzy=f == "exclusions")
            s.tp, s.fp, s.fn = s.tp + tp, s.fp + fp, s.fn + fn
            if fp or fn:
                s.failing_fields.append(f"{k}.{f}")
        for f in (*SCALAR_FIELDS, *LIST_FIELDS):
            empty_g, empty_p = g[f] in (None, []), p[f] in (None, [])
            if empty_g:
                s.halluc_den += 1
                s.halluc += not empty_p
            else:
                s.omit_den += 1
                s.omit += empty_p
    if total:
        s.field_acc = hits / total
    s.exact = s.valid and s.offer_count_ok and not s.failing_fields
    return s


def disagreements(gold: Extraction, pred: Extraction | None) -> int:
    """Field-level disagreement count for the data round-trip gate; invalid output always fails."""
    return len(score(gold, pred).failing_fields) if pred else 99


def summarize(scores: Sequence[SampleScore]) -> dict[str, float]:
    if not scores:
        return {}
    tp, fp, fn = (sum(getattr(s, a) for s in scores) for a in ("tp", "fp", "fn"))
    return {
        "n": len(scores),
        "schema_valid": mean(s.valid for s in scores),
        "field_acc": mean(s.field_acc for s in scores),
        "list_f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0,
        "offer_count_acc": mean(s.offer_count_ok for s in scores),
        "exact_record": mean(s.exact for s in scores),
        "hallucination_rate": sum(s.halluc for s in scores) / max(1, sum(s.halluc_den for s in scores)),
        "omission_rate": sum(s.omit for s in scores) / max(1, sum(s.omit_den for s in scores)),
    }


def percentile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return 0.0
    ordered = sorted(xs)
    return ordered[min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))]


def cost_per_1k_inr(gpu_inr_per_hour: float, throughput_rps: float) -> float:
    return gpu_inr_per_hour / (throughput_rps * 3600) * 1000
