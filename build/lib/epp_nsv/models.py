"""Typed state, verdict, and fixture objects for the public EPP-NSV prototype.

The public package contains constructed, synthetic patient--eye--episode records
only.  Every policy-visible field can carry provenance, assertion, validation,
time, evidence-span, confidence, and missingness metadata so an unsupported
extraction is never silently upgraded into a policy input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Eye(str, Enum):
    """Laterality states represented by the V2 synthetic schema."""

    OD = "OD"
    OS = "OS"
    OU = "OU"
    UNK = "UNK"


class DiseaseFamily(str, Enum):
    """Synthetic disease-family labels used only for explicit scope gating."""

    DR_DME = "DR_DME"
    GLAUCOMA = "GLAUCOMA"
    OTHER = "OTHER"


class Verdict(str, Enum):
    """Conservative, policy-relative verdict vocabulary used by V2."""

    EQUIVALENT = "Equivalent"
    EQUIVALENT_UNDER_GUIDELINE = "Equivalent under Guideline"
    NON_EQUIVALENT = "Non-equivalent"
    INDETERMINATE = "Indeterminate"
    OUT_OF_SCOPE = "Out of scope"
    VERIFICATION_FAILURE = "Verification failure"

    @property
    def is_equivalent(self) -> bool:
        return self in {Verdict.EQUIVALENT, Verdict.EQUIVALENT_UNDER_GUIDELINE}


@dataclass(frozen=True)
class PatientEyeEpisode:
    """Normalised synthetic patient--eye--episode state at an index time.

    Empty policy-critical fields must be represented as ``None``.  The verifier
    then abstains instead of converting absent information into a negative fact.
    ``recorded_treatment_token`` is intentionally retained as an auditable
    leakage-trap field and is never a policy input.
    """

    episode_id: str
    patient_id: str
    eye: Eye | str
    disease_family: DiseaseFamily | str
    observed_at: str

    encounter_token: str | None = None
    age_years: int | None = None
    sex: str | None = None
    hba1c: float | None = None
    egfr: float | None = None

    competing_pathology: bool | None = None
    dr_stage: str | None = None
    macular_edema: bool | None = None
    centre_involvement: bool | None = None
    fundus_neovascularization: bool | None = None
    retinal_detachment: bool | None = None
    active_ocular_infection: bool | None = None
    oct_available: bool | None = None
    image_quality: str | None = None
    visual_acuity_band: str | None = None
    symptom_trajectory: str | None = None
    functional_change_flag: bool | None = None
    prior_retina_review: str | None = None
    prior_anti_vegf_state: str | None = None
    prior_laser_state: str | None = None
    followup_due_band: str | None = None

    # This observed token is excluded from the demonstration policy at t0.
    recorded_treatment_token: str | None = None
    recorded_treatment_at: str | None = None
    clinical_note: str | None = None

    # Field-level evidence metadata. Public fixtures use synthetic tokens only.
    provenance: Mapping[str, str] = field(default_factory=dict)
    evidence_spans: Mapping[str, str] = field(default_factory=dict)
    assertion_status: Mapping[str, str] = field(default_factory=dict)
    validation_status: Mapping[str, str] = field(default_factory=dict)
    field_observed_at: Mapping[str, str] = field(default_factory=dict)
    extraction_confidence: Mapping[str, float] = field(default_factory=dict)

    def field_value(self, name: str) -> Any:
        return getattr(self, name)

    def with_updates(self, **updates: Any) -> "PatientEyeEpisode":
        """Return a copy while retaining all field-level metadata."""
        values = {name: getattr(self, name) for name in self.__dataclass_fields__}
        values.update(updates)
        return PatientEyeEpisode(**values)


@dataclass(frozen=True)
class DecisionVector:
    """The non-prescriptive V2 decision vector.

    The components are abstract policy categories, not observed treatment labels
    and not treatment recommendations.
    """

    scope_status: str
    management_tier: str
    review_urgency_tier: str
    evidence_status: str

    def as_mapping(self) -> dict[str, str]:
        return {
            "scope_status": self.scope_status,
            "management_tier": self.management_tier,
            "review_urgency_tier": self.review_urgency_tier,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True)
class VerificationResult:
    """An auditable outcome of a named-policy comparison."""

    verdict: Verdict
    reasons: tuple[str, ...]
    solver_status: str
    decision_a: DecisionVector | None = None
    decision_b: DecisionVector | None = None
    audit: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PairCase:
    """Synthetic fixture pair plus its policy-relative oracle declaration."""

    case_id: str
    category: str
    observed_a: PatientEyeEpisode
    observed_b: PatientEyeEpisode
    expected_verdict: Verdict
    expected_branch: str
    policy_variant_expected_verdict: Verdict | None = None

    @property
    def gold_equivalent(self) -> bool:
        """Compatibility helper for older callers; not a clinical label."""
        return self.expected_verdict.is_equivalent
