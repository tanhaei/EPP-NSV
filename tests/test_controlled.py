from __future__ import annotations

import json

from epp_nsv.controlled import run_controlled_evaluation


def test_controlled_harness_runs_with_external_csv_and_policy_factory(tmp_path):
    episodes = tmp_path / "episodes.csv"
    episodes.write_text(
        "episode_id,patient_id,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,dr_stage,macular_edema,fundus_neovascularization,retinal_detachment,active_ocular_infection,anti_vegf_hold,fundus_age_days,clinical_note\n"
        "EP-A,PT-A,OD,DR_DME,2026-01-15,55,F,7.8,80,MODERATE,true,false,false,false,false,20,\n"
        "EP-B,PT-B,OD,DR_DME,2026-01-15,74,F,9.9,52,MODERATE,true,false,false,false,false,20,\n",
        encoding="utf-8",
    )
    pairs = tmp_path / "pairs.csv"
    pairs.write_text(
        "pair_id,episode_a_id,episode_b_id,reference_verdict\n"
        "PAIR-1,EP-A,EP-B,Equivalent under Guideline\n",
        encoding="utf-8",
    )
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
    loaded = json.loads((output_dir / "controlled_summary.json").read_text(encoding="utf-8"))
    assert loaded["data_scope"] == "controlled_external_input_not_committed_to_public_repository"
