"""CSV adapter for the V2 patient--eye--episode synthetic schema.

The adapter does not infer missing values.  It preserves empty policy-critical
cells as ``None``; the verifier later returns ``Indeterminate`` unless a
separately auditable lifting contract supplies valid evidence.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from .models import PatientEyeEpisode

_BOOLEAN_FIELDS = {
    "competing_pathology",
    "macular_edema",
    "centre_involvement",
    "fundus_neovascularization",
    "retinal_detachment",
    "active_ocular_infection",
    "oct_available",
    "functional_change_flag",
}
_INTEGER_FIELDS = {"age_years"}
_FLOAT_FIELDS = {"hba1c", "egfr"}
_OPTIONAL_STRING_FIELDS = {
    "encounter_token",
    "sex",
    "dr_stage",
    "image_quality",
    "visual_acuity_band",
    "symptom_trajectory",
    "prior_retina_review",
    "prior_anti_vegf_state",
    "prior_laser_state",
    "followup_due_band",
    "recorded_treatment_token",
    "recorded_treatment_at",
    "clinical_note",
}
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


def _optional_string(value: str | None) -> str | None:
    return None if value is None or value.strip() == "" else value.strip()


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
        "encounter_token",
        "eye",
        "disease_family",
        "observed_at",
        "age_years",
        "sex",
        "hba1c",
        "egfr",
        "competing_pathology",
        "dr_stage",
        "macular_edema",
        "centre_involvement",
        "fundus_neovascularization",
        "retinal_detachment",
        "active_ocular_infection",
        "oct_available",
        "image_quality",
        "visual_acuity_band",
        "symptom_trajectory",
        "functional_change_flag",
        "prior_retina_review",
        "prior_anti_vegf_state",
        "prior_laser_state",
        "followup_due_band",
        "recorded_treatment_token",
        "recorded_treatment_at",
        "clinical_note",
    )


def validate_columns(fieldnames: Iterable[str] | None) -> None:
    available = set(fieldnames or ())
    missing = [name for name in required_columns() if name not in available]
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(missing))


def load_episodes_csv(path: str | Path) -> list[PatientEyeEpisode]:
    """Load the V2 CSV schema without filling missing policy evidence."""
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
                    raw = row.get(field_name)
                    values[field_name] = int(raw) if raw and raw.strip() else None
                for field_name in _FLOAT_FIELDS:
                    raw = row.get(field_name)
                    values[field_name] = float(raw) if raw and raw.strip() else None
                for field_name in _OPTIONAL_STRING_FIELDS:
                    values[field_name] = _optional_string(row.get(field_name))
                for csv_name, model_name in _JSON_METADATA_FIELDS.items():
                    values[model_name] = _optional_json_mapping(row.get(csv_name), csv_name)
                for csv_name in _JSON_METADATA_FIELDS:
                    values.pop(csv_name, None)
                values["episode_id"] = str(values["episode_id"]).strip()
                values["patient_id"] = str(values["patient_id"]).strip()
                values["eye"] = str(values["eye"]).strip()
                values["disease_family"] = str(values["disease_family"]).strip()
                values["observed_at"] = str(values["observed_at"]).strip()
                episodes.append(PatientEyeEpisode(**values))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid episode row {row_number}: {exc}") from exc
    return episodes
