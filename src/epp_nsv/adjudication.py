"""Reference-standard utilities for controlled EPP studies.

These utilities are intentionally data-agnostic.  They make no claim that a
clinical reference standard exists; a governed study must supply one and record
its protocol, raters, eligibility criteria, and adjudication procedure.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .models import Verdict


_ALLOWED_LABELS = {verdict.value for verdict in Verdict}


@dataclass(frozen=True)
class PairReference:
    pair_id: str
    episode_a_id: str
    episode_b_id: str
    reference_verdict: Verdict


def _parse_verdict(value: str) -> Verdict:
    normalized = value.strip()
    if normalized not in _ALLOWED_LABELS:
        raise ValueError(
            f"Unsupported verdict {value!r}; expected one of {sorted(_ALLOWED_LABELS)}"
        )
    return Verdict(normalized)


def load_pair_reference_csv(path: str | Path) -> list[PairReference]:
    """Read a locked pair-level reference standard from a private CSV file."""
    required = {"pair_id", "episode_a_id", "episode_b_id", "reference_verdict"}
    references: list[PairReference] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError("Reference file is missing columns: " + ", ".join(sorted(missing)))
        for row_number, row in enumerate(reader, start=2):
            try:
                references.append(
                    PairReference(
                        pair_id=row["pair_id"],
                        episode_a_id=row["episode_a_id"],
                        episode_b_id=row["episode_b_id"],
                        reference_verdict=_parse_verdict(row["reference_verdict"]),
                    )
                )
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Invalid pair reference row {row_number}: {exc}") from exc
    if len({item.pair_id for item in references}) != len(references):
        raise ValueError("Pair reference file contains duplicate pair_id values")
    return references


def fleiss_kappa(labels_by_item: Mapping[str, Iterable[Verdict]]) -> float | None:
    """Compute Fleiss' kappa for a fully rated, categorical annotation set.

    ``None`` is returned when no valid common-rater set exists.  This function
    is supplied for governed study reproducibility; it does not certify rater
    qualifications or clinical validity.
    """
    rows = [list(labels) for labels in labels_by_item.values()]
    if not rows:
        return None
    ratings_per_item = {len(row) for row in rows}
    if len(ratings_per_item) != 1:
        raise ValueError("Fleiss' kappa requires the same number of ratings per item")
    n_raters = ratings_per_item.pop()
    if n_raters < 2:
        return None

    categories = list(Verdict)
    n_items = len(rows)
    category_totals = Counter(label for row in rows for label in row)
    p_j = {
        category: category_totals[category] / (n_items * n_raters)
        for category in categories
    }
    p_e = sum(value * value for value in p_j.values())

    p_i_values: list[float] = []
    for row in rows:
        counts = Counter(row)
        p_i_values.append(
            sum(count * (count - 1) for count in counts.values())
            / (n_raters * (n_raters - 1))
        )
    p_bar = sum(p_i_values) / n_items
    if p_e == 1:
        return None
    return round((p_bar - p_e) / (1 - p_e), 4)


def load_adjudications_csv(path: str | Path) -> dict[str, list[Verdict]]:
    """Read a private raw-adjudication file for agreement reporting."""
    required = {"pair_id", "adjudicator_id", "verdict"}
    grouped: dict[str, list[Verdict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError("Adjudication file is missing columns: " + ", ".join(sorted(missing)))
        for row_number, row in enumerate(reader, start=2):
            key = (row["pair_id"], row["adjudicator_id"])
            if key in seen:
                raise ValueError(f"Duplicate adjudication at row {row_number}: {key}")
            seen.add(key)
            grouped[row["pair_id"]].append(_parse_verdict(row["verdict"]))
    return dict(grouped)
