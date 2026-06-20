"""Conservative EPP verification with a compiled SMT distinguishing query."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from z3 import Bool, BoolVal, Or, Solver, sat, unsat

from .models import DecisionVector, PatientEyeEpisode, Verdict, VerificationResult
from .policy import DRDMEPolicy
from .semantic_lifting import RuleBasedNoteExtractor


@dataclass
class EPPVerifier:
    """Decision-scoped verifier for the synthetic DR/DME policy.

    The verifier is conservative by default: a disease-scope failure is ``Out
    of scope``; missing or stale safety-critical evidence yields
    ``Indeterminate``; and the public package can emit only ``Equivalent under
    Guideline`` because it evaluates one named demonstration policy.
    """

    policy: DRDMEPolicy
    enable_semantic_lifting: bool = True
    enforce_missingness: bool = True
    enforce_temporal: bool = True
    enforce_domain_gate: bool = True
    use_smt: bool = True
    full_decision_comparison: bool = True

    def __post_init__(self) -> None:
        self._extractor = RuleBasedNoteExtractor()

    def verify(
        self,
        a: PatientEyeEpisode,
        b: PatientEyeEpisode,
    ) -> VerificationResult:
        audit: dict[str, Any] = {
            "policy_id": self.policy.guideline_id,
            "policy_scope": "synthetic_demonstration_policy",
            "semantic_lifting": self.enable_semantic_lifting,
            "semantic_lifting_implementation": (
                "rule_based_synthetic_fixture_extractor"
                if self.enable_semantic_lifting
                else "disabled"
            ),
            "missingness_guard": self.enforce_missingness,
            "temporal_guard": self.enforce_temporal,
            "domain_gate": self.enforce_domain_gate,
            "smt": self.use_smt,
        }

        if self.enforce_domain_gate:
            scope_issues = self.policy.pair_scope_issues(a, b)
            if scope_issues:
                return VerificationResult(
                    verdict=Verdict.OUT_OF_SCOPE,
                    reasons=tuple(scope_issues),
                    solver_status="not_run",
                    audit=audit,
                )

        lifted_a: dict[str, bool] = {}
        lifted_b: dict[str, bool] = {}
        candidates_a = ()
        candidates_b = ()
        if self.enable_semantic_lifting:
            a, lifted_a, candidates_a = self._extractor.apply(a)
            b, lifted_b, candidates_b = self._extractor.apply(b)
        audit["lifted_a"] = lifted_a
        audit["lifted_b"] = lifted_b
        audit["field_provenance_a"] = dict(a.provenance)
        audit["field_provenance_b"] = dict(b.provenance)
        audit["validation_status_a"] = dict(a.validation_status)
        audit["validation_status_b"] = dict(b.validation_status)
        audit["accepted_candidate_count_a"] = len(candidates_a)
        audit["accepted_candidate_count_b"] = len(candidates_b)
        audit["candidate_evidence_a"] = [candidate.evidence_span for candidate in candidates_a]
        audit["candidate_evidence_b"] = [candidate.evidence_span for candidate in candidates_b]

        if self.enforce_missingness:
            issues_a = self.policy.observation_issues(
                a, enforce_temporal=self.enforce_temporal
            )
            issues_b = self.policy.observation_issues(
                b, enforce_temporal=self.enforce_temporal
            )
            if issues_a or issues_b:
                return VerificationResult(
                    verdict=Verdict.INDETERMINATE,
                    reasons=tuple(
                        [f"A:{issue}" for issue in issues_a]
                        + [f"B:{issue}" for issue in issues_b]
                    ),
                    solver_status="not_run",
                    audit=audit,
                )
        else:
            a = self.policy.unsafe_impute_for_ablation(a)
            b = self.policy.unsafe_impute_for_ablation(b)
            audit["unsafe_imputation"] = True

        decision_a = self.policy.decision(a)
        decision_b = self.policy.decision(b)

        if self.use_smt:
            return self._verify_with_smt(a, b, decision_a, decision_b, audit)
        return self._verify_surface_match(decision_a, decision_b, audit)

    @staticmethod
    def _input_bindings(prefix: str, episode: PatientEyeEpisode):
        """Create symbolic inputs and their concrete observational bindings."""
        variables = {
            "retinal_detachment": Bool(f"{prefix}_retinal_detachment"),
            "active_ocular_infection": Bool(f"{prefix}_active_ocular_infection"),
            "stage_is_pdr": Bool(f"{prefix}_stage_is_pdr"),
            "fundus_neovascularization": Bool(
                f"{prefix}_fundus_neovascularization"
            ),
            "macular_edema": Bool(f"{prefix}_macular_edema"),
            "anti_vegf_hold": Bool(f"{prefix}_anti_vegf_hold"),
        }
        values = {
            "retinal_detachment": bool(episode.retinal_detachment),
            "active_ocular_infection": bool(episode.active_ocular_infection),
            "stage_is_pdr": str(episode.dr_stage).upper() == "PDR",
            "fundus_neovascularization": bool(episode.fundus_neovascularization),
            "macular_edema": bool(episode.macular_edema),
            "anti_vegf_hold": bool(episode.anti_vegf_hold),
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
        """Compile policy branches and search for a decision counterexample.

        The query binds observed state variables, compiles the named synthetic
        policy to symbolic output expressions, then asks whether any decision
        component can differ.  Thus the solver validates equality within the
        encoded observation model; it never proves that two real patients are
        clinically identical.
        """
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
        audit["decision_vocabulary_sizes"] = {
            name: len(values) for name, values in codebook.items()
        }
        profile_name = getattr(self.policy, "_profile_name", None)
        if callable(profile_name):
            audit["python_profile_a"] = profile_name(episode_a)
            audit["python_profile_b"] = profile_name(episode_b)
        else:
            audit["python_profile_a"] = "policy_specific_not_exported"
            audit["python_profile_b"] = "policy_specific_not_exported"

        if result == unsat:
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
            return VerificationResult(
                verdict=Verdict.NON_EQUIVALENT,
                reasons=tuple(differences),
                solver_status="sat",
                decision_a=decision_a,
                decision_b=decision_b,
                audit=audit,
            )
        return VerificationResult(
            verdict=Verdict.INDETERMINATE,
            reasons=("solver_unknown",),
            solver_status="unknown",
            decision_a=decision_a,
            decision_b=decision_b,
            audit=audit,
        )

    def _verify_surface_match(
        self,
        a: DecisionVector,
        b: DecisionVector,
        audit: dict[str, Any],
    ) -> VerificationResult:
        """Non-SMT ablation used only in synthetic experiments."""
        if self.full_decision_comparison:
            audit["surface_comparison"] = "full_vector_without_smt"
            differences = self.policy.decision_difference(a, b)
            matches = not differences
        else:
            audit["surface_comparison"] = "treatment_class_only"
            differences = (
                []
                if a.treatment_class == b.treatment_class
                else [
                    f"treatment_class: {a.treatment_class!r} != {b.treatment_class!r}"
                ]
            )
            matches = not differences

        if matches:
            return VerificationResult(
                verdict=Verdict.EQUIVALENT_UNDER_GUIDELINE,
                reasons=("surface_decision_match",),
                solver_status="not_run",
                decision_a=a,
                decision_b=b,
                audit=audit,
            )
        return VerificationResult(
            verdict=Verdict.NON_EQUIVALENT,
            reasons=tuple(differences),
            solver_status="not_run",
            decision_a=a,
            decision_b=b,
            audit=audit,
        )
