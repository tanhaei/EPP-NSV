from __future__ import annotations

import pytest

from epp_nsv.models import DiseaseFamily, Eye, PatientEyeEpisode


@pytest.fixture
def complete_episode() -> PatientEyeEpisode:
    return PatientEyeEpisode(
        episode_id="EP-1",
        patient_id="PT-1",
        eye=Eye.OD,
        disease_family=DiseaseFamily.DR_DME,
        observed_at="2026-01-15",
        age_years=55,
        sex="F",
        hba1c=7.8,
        egfr=80.0,
        dr_stage="MODERATE",
        macular_edema=True,
        fundus_neovascularization=False,
        retinal_detachment=False,
        active_ocular_infection=False,
        anti_vegf_hold=False,
        fundus_age_days=20,
        clinical_note="",
    )
