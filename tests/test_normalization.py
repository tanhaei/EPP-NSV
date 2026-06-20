from __future__ import annotations

from epp_nsv.normalization import load_episodes_csv, required_columns


def test_csv_adapter_preserves_missingness(tmp_path):
    path = tmp_path / "episodes.csv"
    header = list(required_columns())
    row = {
        "episode_id": "EP-1",
        "patient_id": "PT-1",
        "encounter_token": "ENC-1",
        "eye": "OD",
        "disease_family": "DR_DME",
        "observed_at": "2026-01-15",
        "age_years": "55",
        "sex": "F",
        "hba1c": "7.8",
        "egfr": "80",
        "competing_pathology": "false",
        "dr_stage": "MODERATE",
        "macular_edema": "",
        "centre_involvement": "false",
        "fundus_neovascularization": "false",
        "retinal_detachment": "false",
        "active_ocular_infection": "false",
        "oct_available": "true",
        "image_quality": "adequate",
        "visual_acuity_band": "B",
        "symptom_trajectory": "stable",
        "functional_change_flag": "false",
        "prior_retina_review": "none",
        "prior_anti_vegf_state": "none",
        "prior_laser_state": "none",
        "followup_due_band": "not_due",
        "recorded_treatment_token": "",
        "recorded_treatment_at": "",
        "clinical_note": "",
    }
    path.write_text(",".join(header) + "\n" + ",".join(row[name] for name in header) + "\n", encoding="utf-8")
    episodes = load_episodes_csv(path)
    assert len(episodes) == 1
    assert episodes[0].macular_edema is None
    assert episodes[0].oct_available is True
