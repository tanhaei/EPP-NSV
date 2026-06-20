from __future__ import annotations

import json

from epp_nsv.controlled import run_controlled_evaluation
from epp_nsv.normalization import required_columns


def _row(episode_id: str, patient_id: str) -> dict[str, str]:
    return {
        "episode_id": episode_id,
        "patient_id": patient_id,
        "encounter_token": f"ENC-{episode_id}",
        "eye": "OD",
        "disease_family": "DR_DME",
        "observed_at": "2026-01-15",
        "age_years": "55",
        "sex": "F",
        "hba1c": "7.8",
        "egfr": "80",
        "competing_pathology": "false",
        "dr_stage": "MODERATE",
        "macular_edema": "true",
        "centre_involvement": "true",
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


def test_controlled_harness_runs_with_external_csv_and_policy_factory(tmp_path):
    episodes = tmp_path / "episodes.csv"
    header = list(required_columns())
    rows = [_row("EP-A", "PT-A"), _row("EP-B", "PT-B")]
    episodes.write_text(",".join(header) + "\n" + "\n".join(",".join(row[name] for name in header) for row in rows) + "\n", encoding="utf-8")
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("pair_id,episode_a_id,episode_b_id,reference_verdict\nPAIR-1,EP-A,EP-B,Equivalent under Policy\n", encoding="utf-8")
    output_dir = tmp_path / "result"
    summary = run_controlled_evaluation(
        episodes_path=episodes,
        pairs_path=pairs,
        policy_factory="epp_nsv.policy:DRDMEPolicy",
        out_dir=output_dir,
    )
    assert summary["n_pairs"] == 1
    assert (output_dir / "controlled_predictions.csv").exists()
    assert (output_dir / "controlled_summary.json").exists()
    assert (output_dir / "controlled_audit_records.jsonl").exists()
    assert (output_dir / "controlled_run_manifest.json").exists()
    loaded = json.loads((output_dir / "controlled_summary.json").read_text(encoding="utf-8"))
    assert loaded["data_scope"] == "controlled_external_input_not_committed_to_public_repository"
