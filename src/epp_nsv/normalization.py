"""CSV adapter for synthetic fixtures and governed external research runs.

No patient records are bundled with the package.  Callers remain responsible
for operating this adapter only within the approvals, data-use agreement,
privacy controls, and de-identification process applicable to their setting.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from .models import PatientEyeEpisode

_BOOLEAN_FIELDS = {
    "macular_edema",
    "fundus_neovascularization",
    "retinal_detachment",
    "active_ocular_infection",
    "anti_vegf_hold",
}
_INTEGER_FIELDS = {"age_years", "fundus_age_days"}
_FLOAT_FIELDS = {"hba1c", "egfr"}
_JSON_METADATA_FIELDS = {
    "provenance_json": "provenance",
    "evidence_spans_json": "evidence_spans",
    "assertion_status_json": "assertion_status",
    "validation_status_json": "validation_status",
    "field_observed_at_json": "field_observed_at",
    "extraction_confidence_json": "extraction_confidence",
}


def _optional_bool(value: str | None) -> bool | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def _optional_json_mapping(value: str | None, column: str) -> Mapping[str, object]:
    if value is None or value.strip() == "":
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{column} must contain a JSON object")
    return parsed


def required_columns() -> tuple[str, ...]:
    return (
        "episode_id",
        "patient_id",
        "eye",
        "disease_family",
        "observed_at",
        "age_years",
        "sex",
        "hba1c",
        "egfr",
        "dr_stage",
        "macular_edema",
        "fundus_neovascularization",
        "retinal_detachment",
        "active_ocular_infection",
        "anti_vegf_hold",
        "fundus_age_days",
        "clinical_note",
    )


def validate_columns(fieldnames: Iterable[str] | None) -> None:
    available = set(fieldnames or ())
    missing = [name for name in required_columns() if name not in available]
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(missing))


def load_episodes_csv(path: str | Path) -> list[PatientEyeEpisode]:
    """Load the documented minimal schema without silently filling missing facts."""
    episodes: list[PatientEyeEpisode] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        validate_columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            values: dict[str, object] = dict(row)
            try:
                for field_name in _BOOLEAN_FIELDS:
                    values[field_name] = _optional_bool(row.get(field_name))
                for field_name in _INTEGER_FIELDS:
                    value = row.get(field_name)
                    values[field_name] = int(value) if value else None
                for field_name in _FLOAT_FIELDS:
                    value = row.get(field_name)
                    values[field_name] = float(value) if value else None
                for csv_name, model_name in _JSON_METADATA_FIELDS.items():
                    values[model_name] = _optional_json_mapping(row.get(csv_name), csv_name)
                for csv_name in _JSON_METADATA_FIELDS:
                    values.pop(csv_name, None)
                episodes.append(PatientEyeEpisode(**values))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid episode row {row_number}: {exc}") from exc
    return episodes
