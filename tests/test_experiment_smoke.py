from __future__ import annotations

import csv
import json

from epp_nsv.experiments import EXPERIMENT_SCOPE, run_experiment


def test_synthetic_experiment_smoke(tmp_path):
    output_dir = tmp_path / "smoke"
    result = run_experiment(n_pairs=64, seed=17, out_dir=output_dir)

    assert result["n_pairs"] == 64
    required = {
        "fixtures.jsonl",
        "fixture_manifest.json",
        "policy_manifest.json",
        "pair_predictions.csv",
        "audit_records.jsonl",
        "metrics.json",
        "ablation_summary.csv",
        "policy_version_perturbation.jsonl",
        "environment.json",
        "run_metadata.json",
        "run_manifest.json",
        "report.md",
        "generated_table.tex",
    }
    assert required <= {path.name for path in output_dir.iterdir()}

    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["epp_nsv_full"]["fixture_conformance_rate"] == 1.0
    assert metrics["epp_nsv_full"]["expected_indeterminate_abstention_rate"] == 1.0
    assert metrics["epp_nsv_full"]["expected_out_of_scope_rate"] == 1.0

    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["experiment_scope"] == EXPERIMENT_SCOPE
    assert metadata["clinical_performance_claim_permitted"] is False
    assert metadata["policy_hash"]

    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixture_manifest"]["pair_count"] == 64
    assert "fixture_manifest.json" in manifest["artifacts"]
    assert "pair_predictions.csv" in manifest["artifacts"]

    fixture_manifest = json.loads((output_dir / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert fixture_manifest["pair_count"] == 64
    assert fixture_manifest["synthetic_declaration"]
    assert len(fixture_manifest["pair_ids"]) == 64
    assert fixture_manifest["family_ids"]

    with (output_dir / "pair_predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 64 * result["n_methods"]
    assert {row["expected_synthetic_verdict"] for row in rows} >= {
        "Equivalent under Policy",
        "Indeterminate",
        "Non-equivalent",
        "Out of scope",
    }
