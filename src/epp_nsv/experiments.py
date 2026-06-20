"""Executable synthetic verification protocol for the EPP-NSV prototype."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Callable

from .baselines import SimilarityBaseline
from .metrics import evaluate_predictions, verdict_distribution
from .models import PairCase, Verdict, VerificationResult
from .policy import DRDMEPolicy
from .synthetic import build_pair_cases
from .verifier import EPPVerifier


EXPERIMENT_SCOPE = "synthetic_fixture_software_validation_only"


def _methods() -> dict[str, Callable[[PairCase], VerificationResult]]:
    policy = DRDMEPolicy()
    full = EPPVerifier(policy)
    no_missingness = EPPVerifier(policy, enforce_missingness=False)
    no_temporal = EPPVerifier(policy, enforce_temporal=False)
    no_semantic_lifting = EPPVerifier(policy, enable_semantic_lifting=False)
    no_smt = EPPVerifier(policy, use_smt=False, full_decision_comparison=False)
    similarity = SimilarityBaseline()

    return {
        "epp_nsv_full": lambda case: full.verify(case.observed_a, case.observed_b),
        "ablation_no_missingness_guard": lambda case: no_missingness.verify(
            case.observed_a, case.observed_b
        ),
        "ablation_no_temporal_guard": lambda case: no_temporal.verify(
            case.observed_a, case.observed_b
        ),
        "ablation_no_semantic_lifting": lambda case: no_semantic_lifting.verify(
            case.observed_a, case.observed_b
        ),
        "ablation_no_smt_full_vector": lambda case: no_smt.verify(
            case.observed_a, case.observed_b
        ),
        "handcrafted_similarity_baseline": lambda case: similarity.verify(
            case.observed_a, case.observed_b
        ),
    }


def _run_metadata(n_pairs: int, seed: int) -> dict[str, object]:
    return {
        "experiment_scope": EXPERIMENT_SCOPE,
        "data_scope": "synthetic_only_no_bioarc_or_patient_level_data",
        "reference_standard": "synthetic_policy_oracle_not_clinician_adjudication",
        "n_pairs": n_pairs,
        "seed": seed,
        "policy_id": DRDMEPolicy().guideline_id,
        "semantic_lifting": "deterministic_rule_based_fixture_extractor_not_llm",
        "git_commit": os.environ.get("GITHUB_SHA", "unavailable_in_source_archive"),
        "clinical_performance_claim_permitted": False,
    }


def run_experiment(n_pairs: int, seed: int, out_dir: Path) -> dict[str, object]:
    """Run reproducible synthetic experiments and save reviewable artifacts.

    The generated metrics are executable checks against a synthetic oracle.  They
    must not be reported as BioArc, clinician-adjudicated, or clinical-performance
    results.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = build_pair_cases(n_pairs=n_pairs, seed=seed)
    methods = _methods()

    rows: list[dict[str, object]] = []
    metrics: dict[str, dict[str, object]] = {}
    method_predictions: dict[str, list[Verdict]] = {}

    for method_name, method in methods.items():
        predictions: list[Verdict] = []
        for case in cases:
            result = method(case)
            predictions.append(result.verdict)
            rows.append(
                {
                    "experiment_scope": EXPERIMENT_SCOPE,
                    "method": method_name,
                    "case_id": case.case_id,
                    "category": case.category,
                    "gold_label": "Equivalent" if case.gold_equivalent else "Non-equivalent",
                    "gold_source": "synthetic_policy_oracle",
                    "prediction": result.verdict.value,
                    "solver_status": result.solver_status,
                    "reasons": " | ".join(result.reasons),
                }
            )
        metrics[method_name] = {
            **evaluate_predictions(
                [case.gold_equivalent for case in cases], predictions
            ),
            "verdict_distribution": verdict_distribution(predictions),
        }
        method_predictions[method_name] = predictions

    full = method_predictions["epp_nsv_full"]
    similarity = method_predictions["handcrafted_similarity_baseline"]
    comparable = [
        (a, b)
        for a, b in zip(full, similarity)
        if a not in {Verdict.INDETERMINATE, Verdict.OUT_OF_SCOPE}
    ]
    disagreement = (
        sum(a.is_equivalent != b.is_equivalent for a, b in comparable) / len(comparable)
        if comparable
        else None
    )
    metrics["epp_nsv_full"]["similarity_equivalence_disagreement"] = (
        round(disagreement, 4) if disagreement is not None else None
    )

    with (out_dir / "pair_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with (out_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)

    with (out_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(_run_metadata(n_pairs, seed), handle, indent=2, sort_keys=True)

    with (out_dir / "ablation_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "method",
            "equivalence_precision",
            "equivalence_recall",
            "non_equivalence_precision",
            "non_equivalence_recall",
            "indeterminate_rate",
            "coverage",
            "unsafe_equivalence_rate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for method_name, values in metrics.items():
            writer.writerow({name: values.get(name) for name in fieldnames} | {"method": method_name})

    report = _render_report(n_pairs=n_pairs, seed=seed, metrics=metrics)
    (out_dir / "report.md").write_text(report, encoding="utf-8")

    return {
        "n_pairs": n_pairs,
        "seed": seed,
        "out_dir": str(out_dir),
        "metrics": metrics,
        "metadata": _run_metadata(n_pairs, seed),
    }


def _render_report(n_pairs: int, seed: int, metrics: dict[str, dict[str, object]]) -> str:
    lines = [
        "# Synthetic EPP-NSV Experimental Run",
        "",
        f"- Pairs: `{n_pairs}`",
        f"- Seed: `{seed}`",
        "- Data: synthetic only; no BioArc or patient-level data were used.",
        "- Reference standard: synthetic policy oracle; not clinician adjudication.",
        "- Interpretation: validates executable behavior and safety guards, not clinical performance.",
        "",
        "| Method | Eq. precision | Eq. recall | Non-eq. precision | Indeterminate | Unsafe eq. rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method_name, value in metrics.items():
        lines.append(
            "| {name} | {eqp} | {eqr} | {nep} | {ind} | {unsafe} |".format(
                name=method_name,
                eqp=value.get("equivalence_precision"),
                eqr=value.get("equivalence_recall"),
                nep=value.get("non_equivalence_precision"),
                ind=value.get("indeterminate_rate"),
                unsafe=value.get("unsafe_equivalence_rate"),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the synthetic EPP-NSV verification protocol."
    )
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
                "full_metrics": result["metrics"]["epp_nsv_full"],
                "experiment_scope": EXPERIMENT_SCOPE,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
