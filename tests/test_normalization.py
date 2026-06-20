from __future__ import annotations

from epp_nsv.normalization import load_episodes_csv


def test_csv_adapter_preserves_missingness(tmp_path):
    path = tmp_path / "episodes.csv"
    path.write_text(
        "episode_id,patient_id,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,dr_stage,macular_edema,fundus_neovascularization,retinal_detachment,active_ocular_infection,anti_vegf_hold,fundus_age_days,clinical_note\n"
        "EP-1,PT-1,OD,DR_DME,2026-01-15,55,F,7.8,80,MODERATE,,false,false,false,false,10,\n",
        encoding="utf-8",
    )
    episodes = load_episodes_csv(path)
    assert len(episodes) == 1
    assert episodes[0].macular_edema is None
    assert episodes[0].fundus_neovascularization is False
