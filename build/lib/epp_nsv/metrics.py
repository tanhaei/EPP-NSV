"""Synthetic-conformance and controlled-study metric helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

from .models import Verdict


def _safe_div(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def evaluate_synthetic_conformance(
    expected: Iterable[Verdict], predictions: Iterable[Verdict]
) -> dict[str, object]:
    """Exact agreement with a synthetic policy oracle, never clinical accuracy."""
    expected_values, predicted_values = list(expected), list(predictions)
    if len(expected_values) != len(predicted_values):
        raise ValueError("Expected and prediction lengths must match")
    count = len(expected_values)
    correct = sum(a == b for a, b in zip(expected_values, predicted_values))
    per_expected_label: dict[str, dict[str, int | float | None]] = {}
    for label in Verdict:
        indices = [index for index, value in enumerate(expected_values) if value == label]
        if not indices:
            continue
        matches = sum(predicted_values[index] == label for index in indices)
        per_expected_label[label.value] = {
            "n_expected": len(indices),
            "correct": matches,
            "recall": _safe_div(matches, len(indices)),
        }
    return {
        "n_pairs": count,
        "exact_conformance_count": correct,
        "fixture_conformance_rate": _safe_div(correct, count),
        "expected_verdict_distribution": verdict_distribution(expected_values),
        "prediction_verdict_distribution": verdict_distribution(predicted_values),
        "per_expected_verdict": per_expected_label,
    }


def evaluate_predictions(
    gold_equivalent: Iterable[bool], predictions: Iterable[Verdict]
) -> dict[str, float | int | None]:
    """Binary helper retained only for a future controlled-study endpoint."""
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
        "equivalence_precision": _safe_div(eq_tp, eq_tp + eq_fp),
        "equivalence_recall": _safe_div(eq_tp, eq_tp + eq_fn),
        "non_equivalence_precision": _safe_div(ne_tp, ne_tp + ne_fp),
        "non_equivalence_recall": _safe_div(ne_tp, ne_tp + ne_fn),
        "indeterminate_rate": _safe_div(sum(indeterminate), count),
        "coverage": _safe_div(count - sum(indeterminate), count),
        "unsafe_equivalence_rate": _safe_div(eq_fp, eq_tp + eq_fp),
    }


def verdict_distribution(predictions: Iterable[Verdict]) -> Mapping[str, int]:
    return dict(Counter(value.value for value in predictions))
