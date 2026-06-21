"""Independent reference oracle for decision-scoped pair equivalence.

This module is a deliberately *separate* implementation of the pairwise verdict
described by the synthetic policy grammar in the manuscript appendix
(``POLICY DEMO-DRDME-v1``).  It is written against that grammar rather than
against :mod:`epp_nsv.policy`/:mod:`epp_nsv.verifier`, and it shares no decision
logic with them -- it only reuses the typed :mod:`epp_nsv.models` data classes.

Its sole purpose is to provide a second, non-self-referential oracle so that the
agreement reported by the mutation-testing study is not the verifier agreeing
with its own specification.  It is *not* a clinical reference standard.

The implementation is intentionally re-derived from the documented grammar:

* scope/same-eye gate -> ``Out of scope``;
* required pre-index, provenance, validation, assertion, confidence, temporal,
  and missingness guards -> ``Indeterminate``;
* otherwise an abstract decision vector is computed and the pair is
  ``Equivalent under Policy`` iff the two vectors are identical, else
  ``Non-equivalent``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import DecisionVector, Eye, PatientEyeEpisode, Verdict

# Re-declared here on purpose: the oracle must not import the policy's own
# constants, so that a fault injected into the policy cannot silently propagate
# into the oracle.
_CRITICAL_FIELDS: tuple[str, ...] = (
    "dr_stage",
    "macular_edema",
    "centre_involvement",
    "fundus_neovascularization",
    "retinal_detachment",
    "active_ocular_infection",
    "oct_available",
    "image_quality",
    "visual_acuity_band",
    "symptom_trajectory",
    "functional_change_flag",
    "prior_retina_review",
    "prior_anti_vegf_state",
    "prior_laser_state",
    "followup_due_band",
)
_MAX_OBSERVATION_AGE_DAYS = 90
_VALID_VALIDATION = {"fixture_validated", "synthetic_fixture_accepted", "governed_validated"}
_REDUCED_VISION = {"C", "D", "E", "REDUCED"}
_PRIOR_PRESENT_EXCLUDES = {"", "none", "no", "not_documented"}


def _enum(value: object) -> str:
    return str(getattr(value, "value", value))


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class IndependentOracle:
    """A grammar-derived second implementation of the pairwise verdict."""

    non_centre_macular_requires_review: bool = True
    max_observation_age_days: int = _MAX_OBSERVATION_AGE_DAYS

    # --- scope -----------------------------------------------------------
    def _scope_fails(self, a: PatientEyeEpisode, b: PatientEyeEpisode) -> bool:
        for episode in (a, b):
            if _enum(episode.disease_family) != "DR_DME":
                return True
            if episode.competing_pathology is True:
                return True
        eye_a, eye_b = _enum(a.eye), _enum(b.eye)
        if eye_a != Eye.UNK.value and eye_b != Eye.UNK.value and eye_a != eye_b:
            return True
        return False

    # --- evidence sufficiency -------------------------------------------
    def _indeterminate(self, episode: PatientEyeEpisode) -> bool:
        if _enum(episode.eye) == Eye.UNK.value or _enum(episode.eye) not in {m.value for m in Eye}:
            return True
        if episode.competing_pathology is None:
            return True
        index_date = _to_date(episode.observed_at)
        if index_date is None:
            return True
        for name in _CRITICAL_FIELDS:
            value = getattr(episode, name)
            if value is None:
                return True
            if name == "image_quality" and str(value).lower() not in {"adequate", "good"}:
                return True
            if not str(episode.provenance.get(name, "")).strip():
                return True
            if not str(episode.evidence_spans.get(name, "")).strip():
                return True
            assertion = str(episode.assertion_status.get(name, "")).strip().lower()
            if assertion in {"", "uncertain", "contradicted"}:
                return True
            if str(episode.validation_status.get(name, "")).strip().lower() not in _VALID_VALIDATION:
                return True
            confidence = episode.extraction_confidence.get(name)
            if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
                return True
            fact_date = _to_date(episode.field_observed_at.get(name))
            if fact_date is None:
                return True
            if fact_date > index_date:
                return True
            if (index_date - fact_date).days > self.max_observation_age_days:
                return True
        return False

    # --- decision --------------------------------------------------------
    def _has_prior_care(self, episode: PatientEyeEpisode) -> bool:
        return any(
            str(value).lower() not in _PRIOR_PRESENT_EXCLUDES
            for value in (
                episode.prior_retina_review,
                episode.prior_anti_vegf_state,
                episode.prior_laser_state,
            )
        )

    def _decision(self, episode: PatientEyeEpisode) -> DecisionVector:
        reduced = str(episode.visual_acuity_band).upper() in _REDUCED_VISION
        worsening = str(episode.symptom_trajectory).lower() == "worsening"
        overdue = str(episode.followup_due_band).lower() == "overdue"
        if bool(episode.retinal_detachment):
            return DecisionVector("in_scope", "urgent_exception", "immediate", "sufficient")
        if bool(episode.active_ocular_infection):
            return DecisionVector("in_scope", "urgent_exception", "same_day", "sufficient")
        if str(episode.dr_stage).upper() == "PDR" or bool(episode.fundus_neovascularization):
            return DecisionVector("in_scope", "advanced_retinal_review", "expedited", "sufficient")
        if bool(episode.macular_edema):
            if bool(episode.centre_involvement) or reduced or worsening or overdue:
                return DecisionVector("in_scope", "macular_review", "expedited", "sufficient")
            if self._has_prior_care(episode):
                return DecisionVector("in_scope", "macular_review_with_history", "scheduled", "sufficient")
            if self.non_centre_macular_requires_review:
                return DecisionVector("in_scope", "macular_review", "scheduled", "sufficient")
        if bool(episode.functional_change_flag) or overdue:
            return DecisionVector("in_scope", "followup_review", "scheduled", "sufficient")
        return DecisionVector("in_scope", "monitoring", "routine", "sufficient")

    def verdict(self, a: PatientEyeEpisode, b: PatientEyeEpisode) -> Verdict:
        """Return the policy-relative verdict for a pair, independently derived."""
        if self._scope_fails(a, b):
            return Verdict.OUT_OF_SCOPE
        if self._indeterminate(a) or self._indeterminate(b):
            return Verdict.INDETERMINATE
        if self._decision(a).as_mapping() == self._decision(b).as_mapping():
            return Verdict.EQUIVALENT_UNDER_POLICY
        return Verdict.NON_EQUIVALENT
