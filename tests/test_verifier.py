from __future__ import annotations

from epp_nsv.models import DiseaseFamily, Verdict
from epp_nsv.policy import DRDMEPolicy
from epp_nsv.verifier import EPPVerifier


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
    altered = complete_episode.with_updates(macular_edema=False)
    result = verifier.verify(complete_episode, altered)
    assert result.verdict == Verdict.NON_EQUIVALENT
    assert result.solver_status == "sat"
    assert any("treatment_class" in reason for reason in result.reasons)


def test_missing_critical_fundus_fact_abstains(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    incomplete = complete_episode.with_updates(macular_edema=None)
    result = verifier.verify(complete_episode, incomplete)
    assert result.verdict == Verdict.INDETERMINATE
    assert "B:missing:macular_edema" in result.reasons


def test_note_constraint_is_lifted_before_verification(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    a = complete_episode.with_updates(
        anti_vegf_hold=True,
        clinical_note="Documented anti-VEGF held pending review.",
    )
    b = a.with_updates(episode_id="EP-note", anti_vegf_hold=None)
    result = verifier.verify(a, b)
    assert result.verdict == Verdict.EQUIVALENT_UNDER_GUIDELINE
    assert result.audit["lifted_b"] == {"anti_vegf_hold": True}
    assert result.audit["accepted_candidate_count_b"] == 1


def test_stale_observation_abstains(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    stale = complete_episode.with_updates(fundus_age_days=120)
    result = verifier.verify(complete_episode, stale)
    assert result.verdict == Verdict.INDETERMINATE
    assert any("stale:fundus_age_days" in reason for reason in result.reasons)


def test_domain_gate_returns_out_of_scope(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    other = complete_episode.with_updates(disease_family=DiseaseFamily.GLAUCOMA)
    result = verifier.verify(complete_episode, other)
    assert result.verdict == Verdict.OUT_OF_SCOPE
    assert result.reasons == ("disease_scope_not_supported_by_named_policy",)


def test_laterality_gate_returns_out_of_scope(complete_episode):
    verifier = EPPVerifier(DRDMEPolicy())
    other_eye = complete_episode.with_updates(eye="OS")
    result = verifier.verify(complete_episode, other_eye)
    assert result.verdict == Verdict.OUT_OF_SCOPE
    assert result.reasons == ("incompatible_laterality:OD!=OS",)
