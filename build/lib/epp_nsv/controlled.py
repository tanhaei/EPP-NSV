"""Controlled-study harness for externally governed EPP evaluations.

The public repository contains no patient data and no clinical results.  This
module lets an approved private environment run the same auditable verifier on
external de-identified CSV inputs and an externally supplied, approved policy.
It is a harness, not a clinical deployment tool.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
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


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("GITHUB_SHA", "unavailable_in_source_archive")


def _policy_manifest_and_hash(policy: Any) -> tuple[dict[str, Any], str]:
    manifest = (
        policy.policy_manifest()
        if hasattr(policy, "policy_manifest") and callable(policy.policy_manifest)
        else {"policy_id": policy.guideline_id, "contract": "private_policy_factory"}
    )
    policy_hash = (
        policy.policy_hash()
        if hasattr(policy, "policy_hash") and callable(policy.policy_hash)
        else hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()
    )
    return manifest, policy_hash


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
        "critical_fields",
        "domain_ok",
        "pair_scope_issues",
        "pair_observation_issues",
        "observation_issues",
        "fact_audit",
        "decision",
        "unsafe_impute_for_ablation",
        "signature_fields",
        "output_codebook",
        "smt_output_expressions",
        "decision_difference",
        "policy_manifest",
        "policy_hash",
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
    audit_rows: list[dict[str, object]] = []
    full_predictions: list[Verdict] = []
    policy_manifest, policy_hash = _policy_manifest_and_hash(policy)
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
        audit_rows.append(
            {
                "pair_id": reference.pair_id,
                "episode_a_id": reference.episode_a_id,
                "episode_b_id": reference.episode_b_id,
                "policy_id": policy.guideline_id,
                "policy_hash": policy_hash,
                "epp_verdict": result.verdict.value,
                "solver_status": result.solver_status,
                "audit": result.audit,
            }
        )

    with (destination / "controlled_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    with (destination / "controlled_audit_records.jsonl").open("w", encoding="utf-8") as handle:
        for row in audit_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    summary: dict[str, object] = {
        "data_scope": "controlled_external_input_not_committed_to_public_repository",
        "policy_id": policy.guideline_id,
        "policy_hash": policy_hash,
        "policy_manifest": policy_manifest,
        "input_hashes": {
            "episodes.csv": _sha256(episodes_path),
            "pair_reference.csv": _sha256(pairs_path),
            **({"adjudications.csv": _sha256(adjudications_path)} if adjudications_path is not None else {}),
        },
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

    summary_path = destination / "controlled_summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    output_files = [
        destination / "controlled_predictions.csv",
        destination / "controlled_audit_records.jsonl",
        summary_path,
    ]
    run_manifest = {
        "data_scope": "controlled_secure_run_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy_id": policy.guideline_id,
        "policy_hash": policy_hash,
        "code_commit": _git_commit(),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
        },
        "input_hashes": summary["input_hashes"],
        "output_hashes": {path.name: _sha256(path) for path in output_files},
        "mandatory_reporting_reminder": (
            "A clinical manuscript still requires a locked protocol, patient-level partitioning, "
            "a blinded reference standard, prespecified statistics, and governance approval."
        ),
    }
    with (destination / "controlled_run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(run_manifest, handle, indent=2, sort_keys=True)
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
