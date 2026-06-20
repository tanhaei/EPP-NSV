"""Metric calculation for synthetic EPP pair experiments."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

from .models import Verdict


def _safe_div(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def evaluate_predictions(
    gold_equivalent: Iterable[bool], predictions: Iterable[Verdict]
) -> dict[str, float | int | None]:
    gold = list(gold_equivalent)
    pred = list(predictions)
    if len(gold) != len(pred):
        raise ValueError("Gold and prediction lengths must match")

    predicted_equiv = [value.is_equivalent for value in pred]
    predicted_nonequiv = [value == Verdict.NON_EQUIVALENT for value in pred]
    indeterminate = [value == Verdict.INDETERMINATE for value in pred]

    eq_tp = sum(g and p for g, p in zip(gold, predicted_equiv))
    eq_fp = sum((not g) and p for g, p in zip(gold, predicted_equiv))
    eq_fn = sum(g and (not p) for g, p in zip(gold, predicted_equiv))

    ne_tp = sum((not g) and p for g, p in zip(gold, predicted_nonequiv))
    ne_fp = sum(g and p for g, p in zip(gold, predicted_nonequiv))
    ne_fn = sum((not g) and (not p) for g, p in zip(gold, predicted_nonequiv))

    count = len(gold)
    return {
        "n_pairs": count,
        "gold_equivalent": sum(gold),
        "gold_non_equivalent": sum(not g for g in gold),
        "equivalence_precision": _safe_div(eq_tp, eq_tp + eq_fp),
        "equivalence_recall": _safe_div(eq_tp, eq_tp + eq_fn),
        "non_equivalence_precision": _safe_div(ne_tp, ne_tp + ne_fp),
        "non_equivalence_recall": _safe_div(ne_tp, ne_tp + ne_fn),
        "indeterminate_rate": round(sum(indeterminate) / count, 4) if count else None,
        "coverage": round(1 - sum(indeterminate) / count, 4) if count else None,
        "unsafe_equivalence_rate": _safe_div(eq_fp, eq_tp + eq_fp),
        "verdict_equivalent": sum(predicted_equiv),
        "verdict_non_equivalent": sum(predicted_nonequiv),
        "verdict_indeterminate": sum(indeterminate),
    }


def verdict_distribution(predictions: Iterable[Verdict]) -> Mapping[str, int]:
    return dict(Counter(value.value for value in predictions))
