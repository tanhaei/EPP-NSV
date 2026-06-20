from __future__ import annotations

import csv
import json

from epp_nsv.experiments import EXPERIMENT_SCOPE, run_experiment


def test_synthetic_experiment_smoke(tmp_path):
    output_dir = tmp_path / "smoke"
    result = run_experiment(n_pairs=60, seed=17, out_dir=output_dir)

    assert result["n_pairs"] == 60
    assert (output_dir / "pair_predictions.csv").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "run_metadata.json").exists()
    assert (output_dir / "ablation_summary.csv").exists()
    assert (output_dir / "report.md").exists()

    with (output_dir / "metrics.json").open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    assert "epp_nsv_full" in metrics
    assert 0.0 <= metrics["epp_nsv_full"]["coverage"] <= 1.0
    assert metrics["epp_nsv_full"]["verdict_indeterminate"] > 0

    with (output_dir / "run_metadata.json").open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    assert metadata["experiment_scope"] == EXPERIMENT_SCOPE
    assert metadata["clinical_performance_claim_permitted"] is False

    with (output_dir / "pair_predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 60 * 6
    assert {row["gold_source"] for row in rows} == {"synthetic_policy_oracle"}
