"""Mutation testing and independent-oracle agreement for the EPP-NSV verifier.

This module operationalises the manuscript's independent-oracle and
mutation-testing study.  It injects single-point faults into the *policy
object* (the policy encoding and guard logic) and measures whether the real
:class:`~epp_nsv.verifier.EPPVerifier` -- SMT layer included -- detects each
fault by violating the synthetic fixture contract on at least one pair.

Integrity notes
---------------
* Mutant **populations** are generated from explicit, documented operator
  catalogues over the policy's own fields and parameters (see
  :func:`build_mutants`).  The per-class counts are therefore *emergent and
  reproducible*, not magic constants.
* Mutant **kill** outcomes are *measured at run time* by executing the verifier
  against the seeded fixture suite.  Nothing in this file hardcodes a score.
* The independent oracle (:mod:`epp_nsv.independent_oracle`) shares no decision
  logic with the policy/verifier, so the reported agreement rate is not the
  verifier agreeing with its own specification.

The output bundle mirrors the rest of the public run artifacts and additionally
emits a LaTeX table whose columns match the manuscript's mutation-results table
(Mutation class / Mutants / Killed / Mutation score / Notes).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from .independent_oracle import IndependentOracle
from .models import PairCase, PatientEyeEpisode, Verdict, VerificationResult
from .policy import DRDMEPolicy
from .synthetic import build_pair_cases
from .verifier import EPPVerifier

MUTATION_SCOPE = "synthetic_policy_fault_injection_software_validation_only"

# Human-readable labels for the six manuscript mutation classes.
CLASS_LABELS: dict[str, str] = {
    "scope_same_eye": "Negated scope or same-eye guard",
    "temporal_window": "Off-by-one temporal-window bound",
    "laterality_binding": "Relaxed laterality binding",
    "missingness_branch": "Dropped missingness branch",
    "decision_threshold": "Altered decision threshold (tier/urgency)",
    "provenance_validation": "Provenance/validation check removed",
}


# ---------------------------------------------------------------------------
# Mutant policy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MutantPolicy(DRDMEPolicy):
    """A DRDMEPolicy carrying exactly one injected single-point fault.

    ``mut_kind`` selects the faulted method; ``mut_arg`` parameterises it.  Every
    override applies the fault only for its own ``mut_kind`` and otherwise
    defers to the unmutated behaviour, so each mutant differs from the base
    policy in a single location.
    """

    mut_kind: str = ""
    mut_arg: object = None

    # -- scope / same-eye -------------------------------------------------
    def pair_scope_issues(self, a, b, *, enforce_laterality: bool = True) -> list[str]:
        if self.mut_kind == "drop_disease_gate":
            issues: list[str] = []
            if a.competing_pathology is True or b.competing_pathology is True:
                issues.append("competing_pathology_not_supported_by_named_policy")
            if enforce_laterality:
                issues += self._same_eye_issues(a, b)
            return issues
        if self.mut_kind == "drop_competing_gate":
            issues = []
            if not self.domain_ok(a) or not self.domain_ok(b):
                issues.append("disease_scope_not_supported_by_named_policy")
            if enforce_laterality:
                issues += self._same_eye_issues(a, b)
            return issues
        if self.mut_kind == "drop_same_eye":
            return [
                item
                for item in super().pair_scope_issues(a, b, enforce_laterality=False)
            ]
        if self.mut_kind == "same_eye_always_match":
            issues = super().pair_scope_issues(a, b, enforce_laterality=False)
            return issues  # cross-eye no longer flagged
        return super().pair_scope_issues(a, b, enforce_laterality=enforce_laterality)

    def _same_eye_issues(self, a, b) -> list[str]:
        eye_a, eye_b = self._enum_value(a.eye), self._enum_value(b.eye)
        if eye_a != "UNK" and eye_b != "UNK" and eye_a != eye_b:
            return [f"incompatible_laterality:{eye_a}!={eye_b}"]
        return []

    # -- laterality admissibility ----------------------------------------
    def pair_observation_issues(self, a, b) -> list[str]:
        if self.mut_kind == "unk_is_resolved":
            issues = []
            for prefix, episode in (("A", a), ("B", b)):
                if episode.competing_pathology is None:
                    issues.append(f"{prefix}:missing:competing_pathology")
            return issues
        if self.mut_kind == "drop_pair_laterality_check":
            return []
        return super().pair_observation_issues(a, b)

    # -- missingness / temporal / provenance -----------------------------
    def observation_issues(
        self,
        episode,
        *,
        enforce_temporal: bool = True,
        enforce_provenance_validation: bool = True,
    ) -> list[str]:
        base = super().observation_issues(
            episode,
            enforce_temporal=enforce_temporal,
            enforce_provenance_validation=enforce_provenance_validation,
        )
        if self.mut_kind == "drop_missing_field":
            field = str(self.mut_arg)
            return [item for item in base if item != f"missing:{field}"]
        if self.mut_kind == "drop_provenance_subcheck":
            prefix = str(self.mut_arg)
            return [item for item in base if not item.startswith(prefix)]
        if self.mut_kind == "widen_validation":
            field = str(self.mut_arg)
            return [item for item in base if not item.startswith(f"invalid_validation:{field}")]
        return base

    # -- decision threshold ----------------------------------------------
    def _profile_name(self, episode) -> str:
        if self.mut_kind == "threshold_reduced_vision_drop":
            return self._profile_name_with(episode, reduced_drop=str(self.mut_arg))
        if self.mut_kind == "threshold_pdr_drop":
            return self._profile_name_with(episode, pdr_drop=True)
        if self.mut_kind == "threshold_worsening_drop":
            return self._profile_name_with(episode, worsening_drop=True)
        if self.mut_kind == "threshold_overdue_drop":
            return self._profile_name_with(episode, overdue_drop=True)
        return super()._profile_name(episode)

    def _profile_name_with(
        self,
        episode,
        *,
        reduced_drop: str | None = None,
        pdr_drop: bool = False,
        worsening_drop: bool = False,
        overdue_drop: bool = False,
    ) -> str:
        if bool(episode.retinal_detachment):
            return "retinal_urgent_exception"
        if bool(episode.active_ocular_infection):
            return "infection_urgent_exception"
        pdr = (str(episode.dr_stage).upper() == "PDR") and not pdr_drop
        if pdr or bool(episode.fundus_neovascularization):
            return "advanced_retinal_review"
        bands = {"C", "D", "E", "REDUCED"}
        if reduced_drop:
            bands = bands - {reduced_drop}
        reduced_vision = str(episode.visual_acuity_band).upper() in bands
        worsening = (str(episode.symptom_trajectory).lower() == "worsening") and not worsening_drop
        overdue = (str(episode.followup_due_band).lower() == "overdue") and not overdue_drop
        if bool(episode.macular_edema):
            if bool(episode.centre_involvement) or reduced_vision or worsening or overdue:
                return "macular_escalated_review"
            if self._has_prior_care(episode):
                return "macular_history_review"
            if self.non_centre_macular_requires_review:
                return "macular_structured_review"
        if bool(episode.functional_change_flag) or overdue:
            return "functional_followup_review"
        return "monitoring"


def _verifier_for(policy: DRDMEPolicy) -> EPPVerifier:
    return EPPVerifier(policy)


# ---------------------------------------------------------------------------
# Mutant catalogue (emergent counts; see module docstring)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Mutant:
    mutation_class: str
    mutant_id: str
    description: str
    make_policy: Callable[[], DRDMEPolicy]


def build_mutants(base: DRDMEPolicy | None = None) -> list[Mutant]:
    """Enumerate single-point policy mutants from documented operator catalogues."""
    base = base or DRDMEPolicy()
    mutants: list[Mutant] = []

    def add(cls: str, mid: str, desc: str, factory: Callable[[], DRDMEPolicy]) -> None:
        mutants.append(Mutant(cls, f"{cls}:{mid}", desc, factory))

    # 1) scope / same-eye gate
    for kind, desc in (
        ("drop_disease_gate", "remove DR/DME disease gate"),
        ("drop_competing_gate", "remove competing-pathology gate"),
        ("drop_same_eye", "remove same-eye gate"),
        ("same_eye_always_match", "treat any laterality pair as same-eye"),
    ):
        add("scope_same_eye", kind, desc, lambda k=kind: MutantPolicy(mut_kind=k))

    # 2) off-by-one temporal-window bound (parameter offsets + nothing hidden)
    for offset in [o for o in range(-8, 9) if o != 0]:
        add(
            "temporal_window",
            f"max_age{offset:+d}",
            f"max_observation_age_days {base.max_observation_age_days}{offset:+d}",
            lambda o=offset: replace(
                MutantPolicy(mut_kind="temporal_offset"),
                max_observation_age_days=base.max_observation_age_days + o,
            ),
        )

    # 3) relaxed laterality binding
    for kind, desc in (
        ("unk_is_resolved", "treat unresolved laterality as resolved"),
        ("drop_pair_laterality_check", "remove pairwise laterality admissibility check"),
    ):
        add("laterality_binding", kind, desc, lambda k=kind: MutantPolicy(mut_kind=k))

    # 4) dropped missingness branch (one mutant per critical field)
    for field in base.critical_fields:
        add(
            "missingness_branch",
            f"drop_missing_{field}",
            f"do not flag missing {field}",
            lambda f=field: MutantPolicy(mut_kind="drop_missing_field", mut_arg=f),
        )

    # 5) altered decision threshold (tier/urgency)
    for band in ("C", "D", "E", "REDUCED"):
        add(
            "decision_threshold",
            f"reduced_vision_drop_{band}",
            f"drop {band} from reduced-vision set",
            lambda b=band: MutantPolicy(mut_kind="threshold_reduced_vision_drop", mut_arg=b),
        )
    for kind, desc in (
        ("threshold_pdr_drop", "ignore PDR stage in advanced-review branch"),
        ("threshold_worsening_drop", "ignore worsening symptom trajectory"),
        ("threshold_overdue_drop", "ignore overdue follow-up"),
    ):
        add("decision_threshold", kind, desc, lambda k=kind: MutantPolicy(mut_kind=k))
    add(
        "decision_threshold",
        "non_centre_flag_off",
        "disable non-centre macular review requirement",
        lambda: replace(MutantPolicy(mut_kind="non_centre_off"), non_centre_macular_requires_review=False),
    )

    # 6) provenance / validation check removed
    for prefix in ("missing_provenance:", "missing_evidence_span:", "invalid_assertion:", "invalid_confidence:"):
        add(
            "provenance_validation",
            f"drop_{prefix.rstrip(':')}",
            f"remove {prefix.rstrip(':')} guard",
            lambda p=prefix: MutantPolicy(mut_kind="drop_provenance_subcheck", mut_arg=p),
        )
    for field in base.critical_fields:
        add(
            "provenance_validation",
            f"widen_validation_{field}",
            f"accept any validation status for {field}",
            lambda f=field: MutantPolicy(mut_kind="widen_validation", mut_arg=f),
        )

    return mutants


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _suite_violated(policy: DRDMEPolicy, cases: list[PairCase]) -> bool:
    """A mutant is killed if the verifier breaks the fixture contract on any pair.

    The contract is broken either by a verdict that differs from the declared
    expected verdict, or by an unsafe ``Equivalent``/``Equivalent under Policy``
    verdict on a guard fixture that must abstain or be rejected.
    """
    verifier = _verifier_for(policy)
    for case in cases:
        result: VerificationResult = verifier.verify(case.observed_a, case.observed_b)
        if result.verdict != case.expected_verdict:
            return True
        if (
            case.expected_verdict in {Verdict.INDETERMINATE, Verdict.OUT_OF_SCOPE}
            and result.verdict.is_equivalent
        ):
            return True
    return False


def run_mutation_study(n_pairs: int, seed: int, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = build_pair_cases(n_pairs=n_pairs, seed=seed)

    # Sanity: the unmutated verifier must pass the contract before we can claim
    # that a killed mutant was killed *by the contract* rather than by noise.
    base_policy = DRDMEPolicy()
    base_clean = not _suite_violated(base_policy, cases)

    # Independent-oracle agreement on the unmutated verifier.
    oracle = IndependentOracle()
    verifier = _verifier_for(base_policy)
    agree = 0
    for case in cases:
        v = verifier.verify(case.observed_a, case.observed_b).verdict
        if v == oracle.verdict(case.observed_a, case.observed_b):
            agree += 1
    oracle_agreement = round(agree / len(cases), 4) if cases else None

    mutants = build_mutants(base_policy)
    per_class: dict[str, dict[str, object]] = defaultdict(
        lambda: {"mutants": 0, "killed": 0, "survivors": []}
    )
    detail: list[dict[str, object]] = []
    for mutant in mutants:
        killed = _suite_violated(mutant.make_policy(), cases)
        bucket = per_class[mutant.mutation_class]
        bucket["mutants"] = int(bucket["mutants"]) + 1
        if killed:
            bucket["killed"] = int(bucket["killed"]) + 1
        else:
            bucket["survivors"].append(mutant.mutant_id)  # type: ignore[union-attr]
        detail.append(
            {
                "mutation_class": mutant.mutation_class,
                "mutant_id": mutant.mutant_id,
                "description": mutant.description,
                "killed": killed,
            }
        )

    rows: list[dict[str, object]] = []
    total_m = total_k = 0
    for cls in CLASS_LABELS:
        bucket = per_class.get(cls, {"mutants": 0, "killed": 0, "survivors": []})
        m, k = int(bucket["mutants"]), int(bucket["killed"])
        total_m += m
        total_k += k
        rows.append(
            {
                "mutation_class": cls,
                "label": CLASS_LABELS[cls],
                "mutants": m,
                "killed": k,
                "mutation_score": round(k / m, 4) if m else None,
                "survivors": bucket["survivors"],
            }
        )
    overall = {
        "mutants": total_m,
        "killed": total_k,
        "mutation_score": round(total_k / total_m, 4) if total_m else None,
        "independent_oracle_agreement": oracle_agreement,
        "base_contract_clean": base_clean,
    }

    summary = {
        "mutation_scope": MUTATION_SCOPE,
        "n_pairs": n_pairs,
        "seed": seed,
        "policy_id": base_policy.policy_id,
        "policy_hash": base_policy.policy_hash(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "per_class": rows,
        "overall": overall,
        "interpretation_boundary": (
            "synthetic fault-detection on constructed fixtures only; "
            "not a clinical accuracy, safety, or interchangeability claim"
        ),
    }
    (out_dir / "mutation_results.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    _write_csv(out_dir / "mutation_results.csv", rows, overall)
    (out_dir / "mutation_detail.jsonl").write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in detail) + "\n", encoding="utf-8"
    )
    (out_dir / "mutation_results.tex").write_text(_render_table(rows, overall), encoding="utf-8")
    return summary


def _write_csv(path: Path, rows: list[dict[str, object]], overall: dict[str, object]) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mutation_class", "mutants", "killed", "mutation_score"])
        for row in rows:
            writer.writerow([row["label"], row["mutants"], row["killed"], row["mutation_score"]])
        writer.writerow(["Overall", overall["mutants"], overall["killed"], overall["mutation_score"]])


def _render_table(rows: list[dict[str, object]], overall: dict[str, object]) -> str:
    def fmt(score: object) -> str:
        return f"{score:.3f}" if isinstance(score, (int, float)) else "---"

    lines = [
        "% Generated by epp_nsv.mutation; synthetic software validation only.",
        "% Columns match the manuscript mutation-results table.",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"\textbf{Mutation class} & \textbf{Mutants} & \textbf{Killed} & \textbf{Mutation score} \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{row['label']} & {row['mutants']} & {row['killed']} & {fmt(row['mutation_score'])} \\\\"
        )
    lines += [
        r"\midrule",
        f"\\textbf{{Overall}} & {overall['mutants']} & {overall['killed']} & {fmt(overall['mutation_score'])} \\\\",
        f"% independent-oracle agreement: {fmt(overall['independent_oracle_agreement'])}",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EPP-NSV mutation testing and independent-oracle agreement.")
    parser.add_argument("--n-pairs", type=int, default=64)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/mutation_seed17"))
    args = parser.parse_args()
    summary = run_mutation_study(args.n_pairs, args.seed, args.out_dir)
    print(
        json.dumps(
            {
                "n_pairs": summary["n_pairs"],
                "seed": summary["seed"],
                "overall": summary["overall"],
                "out_dir": str(args.out_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
