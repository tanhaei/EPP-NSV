"""Controlled-study harness for externally governed EPP evaluations.

The public repository contains no patient data and no clinical results.  This
module lets an approved private environment run the same auditable verifier on
external de-identified CSV inputs and an externally supplied, approved policy.
It is a harness, not a clinical deployment tool.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .adjudication import (
    PairReference,
    fleiss_kappa,
    load_adjudications_csv,
    load_pair_reference_csv,
)
from .baselines import SimilarityBaseline
from .metrics import evaluate_predictions
from .models import PatientEyeEpisode, Verdict
from .normalization import load_episodes_csv
from .verifier import EPPVerifier


def _load_policy_factory(specification: str):
    """Load a private policy factory using ``package.module:callable`` syntax."""
    module_name, separator, attribute = specification.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("--policy-factory must use the form 'package.module:callable'")
    module = importlib.import_module(module_name)
    factory: Callable[[], Any] = getattr(module, attribute)
    policy = factory()
    required = {
        "guideline_id",
        "domain_ok",
        "pair_scope_issues",
        "observation_issues",
        "decision",
        "unsafe_impute_for_ablation",
        "signature_fields",
        "output_codebook",
        "smt_output_expressions",
        "decision_difference",
    }
    missing = sorted(name for name in required if not hasattr(policy, name))
    if missing:
        raise TypeError("Policy factory returned an incompatible policy: " + ", ".join(missing))
    return policy


def _binary_metrics(references: list[PairReference], predictions: list[Verdict]) -> dict[str, object]:
    binary_reference: list[bool] = []
    binary_prediction: list[Verdict] = []
    excluded: Counter[str] = Counter()
    for reference, prediction in zip(references, predictions):
        if reference.reference_verdict in {Verdict.INDETERMINATE, Verdict.OUT_OF_SCOPE}:
            excluded[reference.reference_verdict.value] += 1
            continue
        binary_reference.append(reference.reference_verdict.is_equivalent)
        binary_prediction.append(prediction)
    return {
        "n_reference_pairs": len(references),
        "n_binary_evaluable_pairs": len(binary_reference),
        "excluded_reference_pairs": dict(excluded),
        "metrics": evaluate_predictions(binary_reference, binary_prediction)
        if binary_reference
        else None,
    }


def run_controlled_evaluation(
    *,
    episodes_path: str | Path,
    pairs_path: str | Path,
    policy_factory: str,
    out_dir: str | Path,
    adjudications_path: str | Path | None = None,
) -> dict[str, object]:
    """Run a private, policy-injected evaluation and write audit-friendly files."""
    episodes = {episode.episode_id: episode for episode in load_episodes_csv(episodes_path)}
    references = load_pair_reference_csv(pairs_path)
    policy = _load_policy_factory(policy_factory)
    verifier = EPPVerifier(policy)
    similarity = SimilarityBaseline()
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    full_predictions: list[Verdict] = []
    for reference in references:
        try:
            episode_a = episodes[reference.episode_a_id]
            episode_b = episodes[reference.episode_b_id]
        except KeyError as exc:
            raise ValueError(
                f"Pair {reference.pair_id} references an unknown episode: {exc.args[0]}"
            ) from exc
        result = verifier.verify(episode_a, episode_b)
        baseline = similarity.verify(episode_a, episode_b)
        full_predictions.append(result.verdict)
        rows.append(
            {
                "pair_id": reference.pair_id,
                "episode_a_id": reference.episode_a_id,
                "episode_b_id": reference.episode_b_id,
                "reference_verdict": reference.reference_verdict.value,
                "epp_verdict": result.verdict.value,
                "epp_solver_status": result.solver_status,
                "epp_reasons": " | ".join(result.reasons),
                "similarity_verdict": baseline.verdict.value,
                "similarity_reasons": " | ".join(baseline.reasons),
            }
        )

    with (destination / "controlled_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    summary: dict[str, object] = {
        "data_scope": "controlled_external_input_not_committed_to_public_repository",
        "policy_id": policy.guideline_id,
        "n_episodes": len(episodes),
        "n_pairs": len(references),
        "reference_verdict_distribution": dict(
            Counter(item.reference_verdict.value for item in references)
        ),
        "epp_verdict_distribution": dict(Counter(item.value for item in full_predictions)),
        "epp_binary_metrics": _binary_metrics(references, full_predictions),
        "warnings": [
            "This harness does not establish clinical validity by itself.",
            "Any clinical result requires a locked protocol, approved policy, and documented adjudication.",
            "Do not commit source episodes, notes, or adjudication files to the public repository.",
        ],
    }
    if adjudications_path is not None:
        adjudications = load_adjudications_csv(adjudications_path)
        summary["adjudication"] = {
            "n_pairs_with_ratings": len(adjudications),
            "fleiss_kappa": fleiss_kappa(adjudications),
            "rating_count_distribution": dict(
                Counter(len(values) for values in adjudications.values())
            ),
        }

    with (destination / "controlled_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a private, externally governed EPP evaluation."
    )
    parser.add_argument("--episodes", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--policy-factory", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--adjudications", type=Path)
    args = parser.parse_args()
    result = run_controlled_evaluation(
        episodes_path=args.episodes,
        pairs_path=args.pairs,
        policy_factory=args.policy_factory,
        out_dir=args.out_dir,
        adjudications_path=args.adjudications,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
