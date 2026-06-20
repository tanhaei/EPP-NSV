from __future__ import annotations

import pytest

from epp_nsv.models import DiseaseFamily, Eye, PatientEyeEpisode
from epp_nsv.policy import DRDMEPolicy


def complete_episode_factory(**updates) -> PatientEyeEpisode:
    policy = DRDMEPolicy()
    values = {
        "episode_id": "EP-1",
        "patient_id": "PT-1",
        "encounter_token": "ENC-1",
        "eye": Eye.OD,
        "disease_family": DiseaseFamily.DR_DME,
        "observed_at": "2026-01-15",
        "age_years": 55,
        "sex": "F",
        "hba1c": 7.8,
        "egfr": 80.0,
        "competing_pathology": False,
        "dr_stage": "MODERATE",
        "macular_edema": True,
        "centre_involvement": True,
        "fundus_neovascularization": False,
        "retinal_detachment": False,
        "active_ocular_infection": False,
        "oct_available": True,
        "image_quality": "adequate",
        "visual_acuity_band": "B",
        "symptom_trajectory": "stable",
        "functional_change_flag": False,
        "prior_retina_review": "none",
        "prior_anti_vegf_state": "none",
        "prior_laser_state": "none",
        "followup_due_band": "not_due",
        "recorded_treatment_token": None,
        "recorded_treatment_at": None,
        "clinical_note": "",
    }
    provenance = {field: "synthetic_fixture_module" for field in policy.critical_fields}
    spans = {field: f"synthetic:{field}" for field in policy.critical_fields}
    assertion = {
        field: ("affirmed" if not isinstance(values[field], bool) or values[field] else "negated")
        for field in policy.critical_fields
    }
    metadata = {
        "provenance": provenance,
        "evidence_spans": spans,
        "assertion_status": assertion,
        "validation_status": {field: "fixture_validated" for field in policy.critical_fields},
        "field_observed_at": {field: "2026-01-10" for field in policy.critical_fields},
        "extraction_confidence": {field: 1.0 for field in policy.critical_fields},
    }
    values.update(metadata)
    values.update(updates)
    return PatientEyeEpisode(**values)


@pytest.fixture
def complete_episode() -> PatientEyeEpisode:
    return complete_episode_factory()
