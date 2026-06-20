from __future__ import annotations

from epp_nsv.models import DiseaseFamily, Eye, Verdict
from epp_nsv.policy import DRDMEPolicy
from epp_nsv.synthetic import build_pair_cases
from epp_nsv.verifier import EPPVerifier


def _without_metadata(episode, field):
    return {
        name: {key: value for key, value in dict(getattr(episode, name)).items() if key != field}
        for name in (
            "provenance",
            "evidence_spans",
            "assertion_status",
            "validation_status",
            "field_observed_at",
            "extraction_confidence",
        )
    }


def test_equivalent_despite_demographic_difference(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    altered = complete_episode.with_updates(
        episode_id="EP-2", patient_id="PT-2", age_years=74, hba1c=9.9, egfr=52.0
    )
    result = verifier.verify(complete_episode, altered)
    assert result.verdict == Verdict.EQUIVALENT_UNDER_GUIDELINE
    assert result.solver_status == "unsat"
    assert result.audit["smt_encoding"] == "compiled_policy_branch_expressions"


def test_decision_critical_difference_is_non_equivalent(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    altered = complete_episode.with_updates(centre_involvement=False)
    result = verifier.verify(complete_episode, altered)
    assert result.verdict == Verdict.NON_EQUIVALENT
    assert result.solver_status == "sat"
    assert any("review_urgency_tier" in reason for reason in result.reasons)
    assert result.audit["counterexample"] is not None


def test_missing_critical_fact_abstains(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    incomplete = complete_episode.with_updates(macular_edema=None, **_without_metadata(complete_episode, "macular_edema"))
    result = verifier.verify(complete_episode, incomplete)
    assert result.verdict == Verdict.INDETERMINATE
    assert "B:missing:macular_edema" in result.reasons


def test_note_constraint_is_lifted_only_when_contract_is_complete(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    metadata = _without_metadata(complete_episode, "macular_edema")
    note_only = complete_episode.with_updates(
        episode_id="EP-note",
        macular_edema=None,
        clinical_note="OD before index: macular oedema present.",
        **metadata,
    )
    result = verifier.verify(complete_episode, note_only)
    assert result.verdict == Verdict.EQUIVALENT_UNDER_GUIDELINE
    assert result.audit["lifted_b"] == {"macular_edema": True}
    assert len(result.audit["accepted_candidates_b"]) == 1


def test_stale_observation_abstains(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    times = dict(complete_episode.field_observed_at)
    times["oct_available"] = "2025-09-01"
    stale = complete_episode.with_updates(field_observed_at=times)
    result = verifier.verify(complete_episode, stale)
    assert result.verdict == Verdict.INDETERMINATE
    assert any("stale:oct_available" in reason for reason in result.reasons)


def test_domain_gate_returns_out_of_scope(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    other = complete_episode.with_updates(disease_family=DiseaseFamily.GLAUCOMA)
    result = verifier.verify(complete_episode, other)
    assert result.verdict == Verdict.OUT_OF_SCOPE
    assert result.reasons == ("disease_scope_not_supported_by_named_policy",)


def test_cross_eye_gate_returns_out_of_scope(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    other_eye = complete_episode.with_updates(eye=Eye.OS)
    result = verifier.verify(complete_episode, other_eye)
    assert result.verdict == Verdict.OUT_OF_SCOPE
    assert result.reasons == ("incompatible_laterality:OD!=OS",)


def test_unresolved_laterality_is_indeterminate_not_out_of_scope(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    unresolved = complete_episode.with_updates(eye=Eye.UNK)
    result = verifier.verify(complete_episode, unresolved)
    assert result.verdict == Verdict.INDETERMINATE
    assert "B:unresolved_laterality" in result.reasons


def test_post_index_treatment_token_is_excluded_from_policy_input(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    with_token = complete_episode.with_updates(
        recorded_treatment_token="synthetic_recorded_management_token",
        recorded_treatment_at="2026-01-16",
    )
    result = verifier.verify(complete_episode, with_token)
    assert result.verdict == Verdict.EQUIVALENT_UNDER_GUIDELINE
    assert any(item["field"] == "recorded_treatment_token" for item in result.audit["rejected_facts_b"])


def test_contradictory_validation_abstains(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    validation = dict(complete_episode.validation_status)
    validation["macular_edema"] = "contradicted"
    contradicted = complete_episode.with_updates(validation_status=validation)
    result = verifier.verify(complete_episode, contradicted)
    assert result.verdict == Verdict.INDETERMINATE
    assert any("invalid_validation:macular_edema=contradicted" in reason for reason in result.reasons)


def test_evidence_graph_and_admissible_fact_audit_are_emitted(complete_episode):
    result = EPPVerifier(DRDMEPolicy()).verify(complete_episode, complete_episode)
    graph = result.audit["evidence_graph_a"]
    assert graph["nodes"]
    assert graph["edges"]
    assert len(result.audit["admissible_facts_a"]) == len(DRDMEPolicy().critical_fields)


def test_policy_version_perturbation_is_recorded_as_a_versioned_change():
    case = next(item for item in build_pair_cases(8, seed=7) if item.category == "policy_version_perturbation")
    base = EPPVerifier(DRDMEPolicy()).verify(case.observed_a, case.observed_b)
    variant = EPPVerifier(
        DRDMEPolicy(
            guideline_id="DEMO-DRDME-v1-perturbed",
            rule_version="v2-synthetic-1-perturbed",
            non_centre_macular_requires_review=False,
        )
    ).verify(case.observed_a, case.observed_b)
    assert base.verdict == Verdict.NON_EQUIVALENT
    assert variant.verdict == Verdict.EQUIVALENT_UNDER_GUIDELINE
