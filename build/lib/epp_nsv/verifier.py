"""Conservative V2 EPP verification with a compiled SMT counterexample query."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from z3 import Bool, BoolVal, Or, Solver, sat, unsat

from .evidence_graph import build_evidence_graph
from .models import DecisionVector, PatientEyeEpisode, Verdict, VerificationResult
from .policy import DRDMEPolicy
from .semantic_lifting import CandidateFact, RuleBasedNoteExtractor


@dataclass
class EPPVerifier:
    """Decision-scoped synthetic verifier with explicit safety guards."""

    policy: DRDMEPolicy
    enable_semantic_lifting: bool = True
    enforce_missingness: bool = True
    enforce_temporal: bool = True
    enforce_domain_gate: bool = True
    enforce_laterality: bool = True
    enforce_provenance_validation: bool = True
    use_smt: bool = True
    full_decision_comparison: bool = True

    def __post_init__(self) -> None:
        self._extractor = RuleBasedNoteExtractor()

    @staticmethod
    def _candidate_payload(candidate: CandidateFact) -> dict[str, Any]:
        return {
            "field": candidate.field_name,
            "value": candidate.value,
            "span": candidate.evidence_span,
            "eye": candidate.eye,
            "time_relation": candidate.time_relation,
            "source_module": candidate.source_module,
            "assertion": candidate.assertion,
            "validation": candidate.validation_status,
            "confidence": candidate.confidence,
        }

    def _base_audit(self) -> dict[str, Any]:
        policy_hash = self.policy.policy_hash() if hasattr(self.policy, "policy_hash") else "unavailable"
        return {
            "policy_id": self.policy.guideline_id,
            "policy_hash": policy_hash,
            "policy_scope": "synthetic_demonstration_policy",
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "semantic_lifting": self.enable_semantic_lifting,
            "semantic_lifting_implementation": (
                "rule_based_synthetic_fixture_extractor" if self.enable_semantic_lifting else "disabled"
            ),
            "missingness_guard": self.enforce_missingness,
            "temporal_guard": self.enforce_temporal,
            "domain_gate": self.enforce_domain_gate,
            "laterality_guard": self.enforce_laterality,
            "provenance_validation_guard": self.enforce_provenance_validation,
            "smt": self.use_smt,
        }

    def verify(self, a: PatientEyeEpisode, b: PatientEyeEpisode) -> VerificationResult:
        audit = self._base_audit()

        if self.enforce_domain_gate:
            scope_issues = self.policy.pair_scope_issues(
                a, b, enforce_laterality=self.enforce_laterality
            )
            audit["scope_issues"] = scope_issues
            audit["scope_status"] = "failed" if scope_issues else "passed"
            if scope_issues:
                return VerificationResult(
                    verdict=Verdict.OUT_OF_SCOPE,
                    reasons=tuple(scope_issues),
                    solver_status="not_run",
                    audit=audit,
                )
        else:
            audit["scope_status"] = "ablation_not_enforced"

        lifted_a: dict[str, Any] = {}
        lifted_b: dict[str, Any] = {}
        accepted_a: tuple[CandidateFact, ...] = ()
        accepted_b: tuple[CandidateFact, ...] = ()
        rejected_a: tuple[CandidateFact, ...] = ()
        rejected_b: tuple[CandidateFact, ...] = ()
        if self.enable_semantic_lifting:
            a, lifted_a, accepted_a, rejected_a = self._extractor.apply(a)
            b, lifted_b, accepted_b, rejected_b = self._extractor.apply(b)
        audit["lifted_a"] = lifted_a
        audit["lifted_b"] = lifted_b
        audit["accepted_candidates_a"] = [self._candidate_payload(item) for item in accepted_a]
        audit["accepted_candidates_b"] = [self._candidate_payload(item) for item in accepted_b]
        audit["rejected_candidates_a"] = [self._candidate_payload(item) for item in rejected_a]
        audit["rejected_candidates_b"] = [self._candidate_payload(item) for item in rejected_b]

        admissible_a, rejected_facts_a = self.policy.fact_audit(
            a,
            enforce_temporal=self.enforce_temporal,
            enforce_provenance_validation=self.enforce_provenance_validation,
        )
        admissible_b, rejected_facts_b = self.policy.fact_audit(
            b,
            enforce_temporal=self.enforce_temporal,
            enforce_provenance_validation=self.enforce_provenance_validation,
        )
        audit["admissible_facts_a"] = admissible_a
        audit["admissible_facts_b"] = admissible_b
        audit["rejected_facts_a"] = rejected_facts_a
        audit["rejected_facts_b"] = rejected_facts_b
        audit["evidence_graph_a"] = build_evidence_graph(
            a, critical_fields=self.policy.critical_fields, policy_id=self.policy.guideline_id
        )
        audit["evidence_graph_b"] = build_evidence_graph(
            b, critical_fields=self.policy.critical_fields, policy_id=self.policy.guideline_id
        )

        if self.enforce_missingness:
            pair_issues = self.policy.pair_observation_issues(a, b) if self.enforce_laterality else []
            issues_a = self.policy.observation_issues(
                a,
                enforce_temporal=self.enforce_temporal,
                enforce_provenance_validation=self.enforce_provenance_validation,
            )
            issues_b = self.policy.observation_issues(
                b,
                enforce_temporal=self.enforce_temporal,
                enforce_provenance_validation=self.enforce_provenance_validation,
            )
            all_issues = pair_issues + [f"A:{issue}" for issue in issues_a] + [f"B:{issue}" for issue in issues_b]
            if all_issues:
                audit["indeterminate_reasons"] = all_issues
                return VerificationResult(
                    verdict=Verdict.INDETERMINATE,
                    reasons=tuple(all_issues),
                    solver_status="not_run",
                    audit=audit,
                )
        else:
            a = self.policy.unsafe_impute_for_ablation(a)
            b = self.policy.unsafe_impute_for_ablation(b)
            audit["unsafe_imputation"] = True

        decision_a = self.policy.decision(
            a,
            enforce_temporal=self.enforce_temporal,
            enforce_provenance_validation=self.enforce_provenance_validation,
        )
        decision_b = self.policy.decision(
            b,
            enforce_temporal=self.enforce_temporal,
            enforce_provenance_validation=self.enforce_provenance_validation,
        )

        if self.use_smt:
            return self._verify_with_smt(a, b, decision_a, decision_b, audit)
        return self._verify_without_counterexample(decision_a, decision_b, audit)

    @staticmethod
    def _input_bindings(prefix: str, episode: PatientEyeEpisode):
        variables = {
            "retinal_detachment": Bool(f"{prefix}_retinal_detachment"),
            "active_ocular_infection": Bool(f"{prefix}_active_ocular_infection"),
            "stage_is_pdr": Bool(f"{prefix}_stage_is_pdr"),
            "fundus_neovascularization": Bool(f"{prefix}_fundus_neovascularization"),
            "macular_edema": Bool(f"{prefix}_macular_edema"),
            "centre_involvement": Bool(f"{prefix}_centre_involvement"),
            "reduced_vision": Bool(f"{prefix}_reduced_vision"),
            "worsening_symptoms": Bool(f"{prefix}_worsening_symptoms"),
            "functional_change": Bool(f"{prefix}_functional_change"),
            "followup_overdue": Bool(f"{prefix}_followup_overdue"),
            "has_prior_care": Bool(f"{prefix}_has_prior_care"),
        }
        prior_values = (
            episode.prior_retina_review,
            episode.prior_anti_vegf_state,
            episode.prior_laser_state,
        )
        values = {
            "retinal_detachment": bool(episode.retinal_detachment),
            "active_ocular_infection": bool(episode.active_ocular_infection),
            "stage_is_pdr": str(episode.dr_stage).upper() == "PDR",
            "fundus_neovascularization": bool(episode.fundus_neovascularization),
            "macular_edema": bool(episode.macular_edema),
            "centre_involvement": bool(episode.centre_involvement),
            "reduced_vision": str(episode.visual_acuity_band).upper() in {"C", "D", "E", "REDUCED"},
            "worsening_symptoms": str(episode.symptom_trajectory).lower() == "worsening",
            "functional_change": bool(episode.functional_change_flag),
            "followup_overdue": str(episode.followup_due_band).lower() == "overdue",
            "has_prior_care": any(str(value).lower() not in {"", "none", "no", "not_documented"} for value in prior_values),
        }
        return variables, values

    def _verify_with_smt(
        self,
        episode_a: PatientEyeEpisode,
        episode_b: PatientEyeEpisode,
        decision_a: DecisionVector,
        decision_b: DecisionVector,
        audit: dict[str, Any],
    ) -> VerificationResult:
        solver = Solver()
        a_vars, a_values = self._input_bindings("a", episode_a)
        b_vars, b_values = self._input_bindings("b", episode_b)
        for name, value in a_values.items():
            solver.add(a_vars[name] == BoolVal(value))
        for name, value in b_values.items():
            solver.add(b_vars[name] == BoolVal(value))

        codebook = self.policy.output_codebook()
        a_out = self.policy.smt_output_expressions(codebook=codebook, **a_vars)
        b_out = self.policy.smt_output_expressions(codebook=codebook, **b_vars)
        fields = tuple(self.policy.signature_fields())
        solver.add(Or(*[a_out[name] != b_out[name] for name in fields]))
        result = solver.check()

        audit["smt_encoding"] = "compiled_policy_branch_expressions"
        audit["observation_fields"] = fields
        audit["input_binding_a"] = a_values
        audit["input_binding_b"] = b_values
        audit["decision_vocabulary_sizes"] = {name: len(values) for name, values in codebook.items()}
        profile_name = getattr(self.policy, "_profile_name", None)
        audit["policy_branch_a"] = (
            profile_name(episode_a) if callable(profile_name) else "policy_specific_not_exported"
        )
        audit["policy_branch_b"] = (
            profile_name(episode_b) if callable(profile_name) else "policy_specific_not_exported"
        )

        if result == unsat:
            audit["counterexample"] = None
            return VerificationResult(
                verdict=Verdict.EQUIVALENT_UNDER_GUIDELINE,
                reasons=("decision_vector_equal_under_named_policy",),
                solver_status="unsat",
                decision_a=decision_a,
                decision_b=decision_b,
                audit=audit,
            )
        if result == sat:
            differences = self.policy.decision_difference(decision_a, decision_b)
            audit["counterexample"] = {
                "policy_branches": [audit["policy_branch_a"], audit["policy_branch_b"]],
                "decision_components": differences,
                "distinguishing_input_bindings": {
                    name: {"A": a_values[name], "B": b_values[name]}
                    for name in a_values
                    if a_values[name] != b_values[name]
                },
            }
            return VerificationResult(
                verdict=Verdict.NON_EQUIVALENT,
                reasons=tuple(differences),
                solver_status="sat",
                decision_a=decision_a,
                decision_b=decision_b,
                audit=audit,
            )
        audit["verification_failure"] = "solver_unknown"
        return VerificationResult(
            verdict=Verdict.VERIFICATION_FAILURE,
            reasons=("solver_unknown",),
            solver_status="unknown",
            decision_a=decision_a,
            decision_b=decision_b,
            audit=audit,
        )

    def _verify_without_counterexample(
        self,
        decision_a: DecisionVector,
        decision_b: DecisionVector,
        audit: dict[str, Any],
    ) -> VerificationResult:
        fields = tuple(self.policy.signature_fields()) if self.full_decision_comparison else ("management_tier",)
        differences = self.policy.decision_difference(decision_a, decision_b, fields)
        audit["smt_encoding"] = "not_run_policy_outputs_compared_directly"
        audit["counterexample"] = None
        if not differences:
            return VerificationResult(
                verdict=Verdict.EQUIVALENT_UNDER_GUIDELINE,
                reasons=("policy_outputs_equal_without_counterexample_query",),
                solver_status="not_run",
                decision_a=decision_a,
                decision_b=decision_b,
                audit=audit,
            )
        return VerificationResult(
            verdict=Verdict.NON_EQUIVALENT,
            reasons=("policy_outputs_differ_without_counterexample_query",),
            solver_status="not_run",
            decision_a=decision_a,
            decision_b=decision_b,
            audit=audit,
        )
