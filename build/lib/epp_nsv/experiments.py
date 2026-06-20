"""Executable V2 synthetic-fixture software-validation protocol."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Callable

from .baselines import SimilarityBaseline
from .metrics import evaluate_synthetic_conformance
from .models import PairCase, Verdict, VerificationResult
from .policy import DRDMEPolicy
from .synthetic import FIXTURE_VERSION, build_pair_cases, episode_to_dict
from .verifier import EPPVerifier

EXPERIMENT_SCOPE = "synthetic_fixture_software_validation_only"


def _methods() -> dict[str, Callable[[PairCase], VerificationResult]]:
    policy = DRDMEPolicy()
    full = EPPVerifier(policy)
    direct_policy = EPPVerifier(policy, use_smt=False)
    no_scope = EPPVerifier(policy, enforce_domain_gate=False)
    no_laterality = EPPVerifier(policy, enforce_laterality=False)
    no_temporal = EPPVerifier(policy, enforce_temporal=False)
    missing_as_absent = EPPVerifier(policy, enforce_missingness=False, enforce_provenance_validation=False)
    no_provenance = EPPVerifier(policy, enforce_provenance_validation=False)
    similarity = SimilarityBaseline()
    return {
        "epp_nsv_full": lambda case: full.verify(case.observed_a, case.observed_b),
        "policy_evaluator_without_counterexample_query": lambda case: direct_policy.verify(case.observed_a, case.observed_b),
        "ablation_remove_scope_gate": lambda case: no_scope.verify(case.observed_a, case.observed_b),
        "ablation_collapse_laterality": lambda case: no_laterality.verify(case.observed_a, case.observed_b),
        "ablation_remove_temporal_filter": lambda case: no_temporal.verify(case.observed_a, case.observed_b),
        "ablation_treat_missing_as_absent": lambda case: missing_as_absent.verify(case.observed_a, case.observed_b),
        "ablation_remove_provenance_validation": lambda case: no_provenance.verify(case.observed_a, case.observed_b),
        "handcrafted_similarity_baseline": lambda case: similarity.verify(case.observed_a, case.observed_b),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("GITHUB_SHA", "unavailable_in_source_archive")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _environment() -> dict[str, object]:
    versions: dict[str, str] = {}
    for package in ("epp-nsv-bioarc", "z3-solver", "pytest"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dependency_versions": versions,
        "git_commit": _git_commit(),
    }


def _case_payload(case: PairCase) -> dict[str, object]:
    return {
        "fixture_version": FIXTURE_VERSION,
        "case_id": case.case_id,
        "category": case.category,
        "expected_synthetic_verdict": case.expected_verdict.value,
        "expected_policy_branch": case.expected_branch,
        "policy_variant_expected_verdict": (
            case.policy_variant_expected_verdict.value if case.policy_variant_expected_verdict else None
        ),
        "episode_a": episode_to_dict(case.observed_a),
        "episode_b": episode_to_dict(case.observed_b),
    }


def _audit_row(method: str, case: PairCase, result: VerificationResult) -> dict[str, object]:
    return {
        "experiment_scope": EXPERIMENT_SCOPE,
        "method": method,
        "case_id": case.case_id,
        "category": case.category,
        "expected_synthetic_verdict": case.expected_verdict.value,
        "predicted_verdict": result.verdict.value,
        "solver_status": result.solver_status,
        "audit": result.audit,
    }


def _method_safety_checks(cases: list[PairCase], results: list[VerificationResult]) -> dict[str, object]:
    pairs = list(zip(cases, results))
    non_equivalent = [result for case, result in pairs if case.expected_verdict == Verdict.NON_EQUIVALENT]
    indeterminate = [result for case, result in pairs if case.expected_verdict == Verdict.INDETERMINATE]
    out_scope = [result for case, result in pairs if case.expected_verdict == Verdict.OUT_OF_SCOPE]
    counterexample = [
        result
        for result in non_equivalent
        if result.verdict == Verdict.NON_EQUIVALENT and bool(result.audit.get("counterexample"))
    ]
    return {
        "expected_non_equivalent_counterexample_rate": (
            round(len(counterexample) / len(non_equivalent), 4) if non_equivalent else None
        ),
        "expected_indeterminate_abstention_rate": (
            round(sum(result.verdict == Verdict.INDETERMINATE for result in indeterminate) / len(indeterminate), 4)
            if indeterminate
            else None
        ),
        "expected_out_of_scope_rate": (
            round(sum(result.verdict == Verdict.OUT_OF_SCOPE for result in out_scope) / len(out_scope), 4)
            if out_scope
            else None
        ),
        "unsafe_equivalence_on_guard_fixtures": sum(
            result.verdict.is_equivalent
            for case, result in pairs
            if case.expected_verdict in {Verdict.INDETERMINATE, Verdict.OUT_OF_SCOPE}
        ),
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _render_report(n_pairs: int, seed: int, metrics: dict[str, dict[str, object]]) -> str:
    lines = [
        "# Synthetic EPP-NSV Software-Validation Run",
        "",
        f"- Fixture version: `{FIXTURE_VERSION}`",
        f"- Pairs: `{n_pairs}`",
        f"- Seed: `{seed}`",
        "- Data: constructed synthetic fixtures only; no BioArc or patient-level data were used.",
        "- Oracle: versioned synthetic policy; not clinician adjudication or clinical truth.",
        "- Interpretation: software conformance and guard behaviour only; not clinical accuracy, safety, coverage, or treatment validity.",
        "",
        "| Method | Fixture conformance | Counterexample availability | Indeterminate abstention | Scope safety |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in metrics.items():
        lines.append(
            "| {name} | {conformance} | {counterexample} | {indeterminate} | {scope} |".format(
                name=name,
                conformance=values.get("fixture_conformance_rate"),
                counterexample=values.get("expected_non_equivalent_counterexample_rate"),
                indeterminate=values.get("expected_indeterminate_abstention_rate"),
                scope=values.get("expected_out_of_scope_rate"),
            )
        )
    return "\n".join(lines) + "\n"


def _render_generated_table(metrics: dict[str, dict[str, object]]) -> str:
    full = metrics["epp_nsv_full"]
    return "\n".join(
        [
            "% Generated from a synthetic software-validation run; do not label as clinical performance.",
            f"\\newcommand{{\\EPPNSVFixtureConformance}}{{{full.get('fixture_conformance_rate')}}}",
            f"\\newcommand{{\\EPPNSVCounterexampleAvailability}}{{{full.get('expected_non_equivalent_counterexample_rate')}}}",
            f"\\newcommand{{\\EPPNSVIndeterminateAbstention}}{{{full.get('expected_indeterminate_abstention_rate')}}}",
            f"\\newcommand{{\\EPPNSVScopeSafety}}{{{full.get('expected_out_of_scope_rate')}}}",
            "",
        ]
    )


def _fixture_manifest(cases: list[PairCase], seed: int) -> dict[str, object]:
    """Describe constructed fixtures without exposing any real-patient data."""
    family_by_pair = {case.case_id: case.category for case in cases}
    family_counts: dict[str, int] = {}
    for category in family_by_pair.values():
        family_counts[category] = family_counts.get(category, 0) + 1
    return {
        "fixture_version": FIXTURE_VERSION,
        "seed": seed,
        "synthetic_declaration": "fresh_constructed_fixtures_no_bioarc_or_patient_level_data",
        "fixture_file": "fixtures.jsonl",
        "pair_count": len(cases),
        "pair_ids": list(family_by_pair),
        "family_ids": sorted(family_counts),
        "family_by_pair": family_by_pair,
        "family_counts": family_counts,
    }


def _policy_version_comparison(cases: list[PairCase]) -> list[dict[str, object]]:
    variant = DRDMEPolicy(
        guideline_id="DEMO-DRDME-v1-perturbed",
        rule_version="v2-synthetic-1-perturbed",
        non_centre_macular_requires_review=False,
    )
    verifier = EPPVerifier(variant)
    rows: list[dict[str, object]] = []
    for case in cases:
        if case.policy_variant_expected_verdict is None:
            continue
        result = verifier.verify(case.observed_a, case.observed_b)
        rows.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "base_policy_id": DRDMEPolicy().guideline_id,
                "variant_policy_id": variant.guideline_id,
                "variant_policy_hash": variant.policy_hash(),
                "expected_variant_verdict": case.policy_variant_expected_verdict.value,
                "actual_variant_verdict": result.verdict.value,
                "solver_status": result.solver_status,
                "policy_version_difference_recorded": True,
            }
        )
    return rows


def run_experiment(n_pairs: int, seed: int, out_dir: Path) -> dict[str, object]:
    """Run V2 synthetic fixtures and write an auditable public run bundle."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = build_pair_cases(n_pairs=n_pairs, seed=seed)
    methods = _methods()
    expected = [case.expected_verdict for case in cases]

    prediction_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    metrics: dict[str, dict[str, object]] = {}
    results_by_method: dict[str, list[VerificationResult]] = {}

    for method_name, method in methods.items():
        results: list[VerificationResult] = []
        for case in cases:
            result = method(case)
            results.append(result)
            prediction_rows.append(
                {
                    "experiment_scope": EXPERIMENT_SCOPE,
                    "method": method_name,
                    "case_id": case.case_id,
                    "category": case.category,
                    "expected_synthetic_verdict": case.expected_verdict.value,
                    "expected_policy_branch": case.expected_branch,
                    "prediction": result.verdict.value,
                    "solver_status": result.solver_status,
                    "reasons": " | ".join(result.reasons),
                }
            )
            audit_rows.append(_audit_row(method_name, case, result))
        metrics[method_name] = {
            **evaluate_synthetic_conformance(expected, [result.verdict for result in results]),
            **_method_safety_checks(cases, results),
        }
        results_by_method[method_name] = results

    policy = DRDMEPolicy()
    fixture_rows = [_case_payload(case) for case in cases]
    fixture_manifest = _fixture_manifest(cases, seed)
    _write_jsonl(out_dir / "fixtures.jsonl", fixture_rows)
    (out_dir / "fixture_manifest.json").write_text(
        json.dumps(fixture_manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    _write_jsonl(out_dir / "audit_records.jsonl", audit_rows)
    _write_jsonl(out_dir / "policy_version_perturbation.jsonl", _policy_version_comparison(cases))

    with (out_dir / "pair_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(prediction_rows[0]))
        writer.writeheader()
        writer.writerows(prediction_rows)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "policy_manifest.json").write_text(
        json.dumps(policy.policy_manifest() | {"policy_hash": policy.policy_hash()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "environment.json").write_text(json.dumps(_environment(), indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(n_pairs, seed, metrics), encoding="utf-8")
    (out_dir / "generated_table.tex").write_text(_render_generated_table(metrics), encoding="utf-8")

    summary_fields = [
        "method",
        "fixture_conformance_rate",
        "expected_non_equivalent_counterexample_rate",
        "expected_indeterminate_abstention_rate",
        "expected_out_of_scope_rate",
        "unsafe_equivalence_on_guard_fixtures",
    ]
    with (out_dir / "ablation_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        for method_name, values in metrics.items():
            writer.writerow({"method": method_name} | {field: values.get(field) for field in summary_fields[1:]})

    metadata = {
        "experiment_scope": EXPERIMENT_SCOPE,
        "fixture_version": FIXTURE_VERSION,
        "synthetic_declaration": "fresh_constructed_fixtures_no_bioarc_or_patient_level_data",
        "reference_standard": "synthetic_policy_oracle_not_clinician_adjudication",
        "n_pairs": n_pairs,
        "seed": seed,
        "policy_id": policy.guideline_id,
        "policy_hash": policy.policy_hash(),
        "semantic_lifting": "deterministic_rule_based_fixture_extractor_not_llm",
        "clinical_performance_claim_permitted": False,
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    artifact_files = [
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
        "report.md",
        "generated_table.tex",
    ]
    source_root = Path(__file__).resolve().parents[2]
    lock_path = source_root / "requirements.lock"
    manifest = {
        "fixture_manifest": {
            "file": "fixture_manifest.json",
            "version": fixture_manifest["fixture_version"],
            "seed": fixture_manifest["seed"],
            "pair_count": fixture_manifest["pair_count"],
            "family_ids": fixture_manifest["family_ids"],
        },
        "policy_manifest": {"policy_id": policy.guideline_id, "policy_hash": policy.policy_hash()},
        "command": f"python -m epp_nsv.experiments --n-pairs {n_pairs} --seed {seed} --out-dir {out_dir}",
        "environment_file": "environment.json",
        "dependency_lock": {
            "path": str(lock_path.name),
            "sha256": _sha256(lock_path) if lock_path.exists() else "missing",
        },
        "code_commit": _git_commit(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {name: _sha256(out_dir / name) for name in artifact_files},
        "interpretation_boundary": "synthetic software-validation run only; not clinical evaluation",
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "n_pairs": n_pairs,
        "seed": seed,
        "out_dir": str(out_dir),
        "n_methods": len(methods),
        "metrics": metrics,
        "metadata": metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V2 synthetic EPP-NSV software validation.")
    parser.add_argument("--n-pairs", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/experiment"))
    args = parser.parse_args()
    result = run_experiment(args.n_pairs, args.seed, args.out_dir)
    print(
        json.dumps(
            {
                "n_pairs": result["n_pairs"],
                "seed": result["seed"],
                "out_dir": result["out_dir"],
                "full_fixture_conformance": result["metrics"]["epp_nsv_full"]["fixture_conformance_rate"],
                "experiment_scope": EXPERIMENT_SCOPE,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
