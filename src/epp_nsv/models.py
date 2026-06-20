"""Typed objects for EPP-NSV experiments and controlled-study adapters.

The public package is a research prototype.  The data model preserves the
minimum evidence metadata required to avoid turning an unsupported extraction
into a clinical fact: laterality, observation time, provenance, assertion,
validation status, confidence, and missingness remain attached to each field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Eye(str, Enum):
    """Laterality values supported by the public prototype."""

    OD = "OD"
    OS = "OS"
    OU = "OU"


class DiseaseFamily(str, Enum):
    """Disease-family labels used for scope gating, not diagnosis."""

    DR_DME = "DR_DME"
    GLAUCOMA = "GLAUCOMA"
    OTHER = "OTHER"


class Verdict(str, Enum):
    """Conservative, model-relative EPP verdicts.

    ``Equivalent`` is reserved for comparison across an approved policy set.
    The released prototype uses a single named demonstration policy and therefore
    emits ``Equivalent under Guideline`` rather than unqualified equivalence.
    """

    EQUIVALENT = "Equivalent"
    EQUIVALENT_UNDER_GUIDELINE = "Equivalent under Guideline"
    NON_EQUIVALENT = "Non-equivalent"
    INDETERMINATE = "Indeterminate"
    OUT_OF_SCOPE = "Out of scope"

    @property
    def is_equivalent(self) -> bool:
        return self in {Verdict.EQUIVALENT, Verdict.EQUIVALENT_UNDER_GUIDELINE}


@dataclass(frozen=True)
class PatientEyeEpisode:
    """A normalized per-eye state for a specified decision time.

    ``None`` means that a value is unavailable in the observation model; it is
    never interpreted as a negative finding by the conservative verifier.  The
    object deliberately does not model an entire clinical record.  It is the
    minimal public representation required by the synthetic DR/DME policy and
    the controlled-study adapter.
    """

    episode_id: str
    patient_id: str
    eye: Eye | str
    disease_family: DiseaseFamily | str
    observed_at: str

    age_years: int | None = None
    sex: str | None = None
    hba1c: float | None = None
    egfr: float | None = None

    dr_stage: str | None = None
    macular_edema: bool | None = None
    fundus_neovascularization: bool | None = None
    retinal_detachment: bool | None = None
    active_ocular_infection: bool | None = None
    anti_vegf_hold: bool | None = None
    fundus_age_days: int | None = None

    clinical_note: str | None = None

    # Field-level evidence metadata.  Public fixtures use benign example values;
    # real records must be supplied only in a governed environment.
    provenance: Mapping[str, str] = field(default_factory=dict)
    evidence_spans: Mapping[str, str] = field(default_factory=dict)
    assertion_status: Mapping[str, str] = field(default_factory=dict)
    validation_status: Mapping[str, str] = field(default_factory=dict)
    field_observed_at: Mapping[str, str] = field(default_factory=dict)
    extraction_confidence: Mapping[str, float] = field(default_factory=dict)

    def field_value(self, name: str) -> Any:
        return getattr(self, name)

    def with_updates(self, **updates: Any) -> "PatientEyeEpisode":
        """Return a copy while retaining field-level evidence metadata."""
        values = {
            "episode_id": self.episode_id,
            "patient_id": self.patient_id,
            "eye": self.eye,
            "disease_family": self.disease_family,
            "observed_at": self.observed_at,
            "age_years": self.age_years,
            "sex": self.sex,
            "hba1c": self.hba1c,
            "egfr": self.egfr,
            "dr_stage": self.dr_stage,
            "macular_edema": self.macular_edema,
            "fundus_neovascularization": self.fundus_neovascularization,
            "retinal_detachment": self.retinal_detachment,
            "active_ocular_infection": self.active_ocular_infection,
            "anti_vegf_hold": self.anti_vegf_hold,
            "fundus_age_days": self.fundus_age_days,
            "clinical_note": self.clinical_note,
            "provenance": dict(self.provenance),
            "evidence_spans": dict(self.evidence_spans),
            "assertion_status": dict(self.assertion_status),
            "validation_status": dict(self.validation_status),
            "field_observed_at": dict(self.field_observed_at),
            "extraction_confidence": dict(self.extraction_confidence),
        }
        values.update(updates)
        return PatientEyeEpisode(**values)


@dataclass(frozen=True)
class DecisionVector:
    """Decision-scoped output used for equality checking in a named policy."""

    urgency: str
    management_domain: str
    treatment_class: str
    safety_constraints: tuple[str, ...]
    follow_up_window: str
    referral: str
    required_tests: tuple[str, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "urgency": self.urgency,
            "management_domain": self.management_domain,
            "treatment_class": self.treatment_class,
            "safety_constraints": self.safety_constraints,
            "follow_up_window": self.follow_up_window,
            "referral": self.referral,
            "required_tests": self.required_tests,
        }


@dataclass(frozen=True)
class VerificationResult:
    """An auditable policy-relative verification outcome."""

    verdict: Verdict
    reasons: tuple[str, ...]
    solver_status: str
    decision_a: DecisionVector | None = None
    decision_b: DecisionVector | None = None
    audit: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PairCase:
    """A synthetic pair with a policy-oracle label.

    ``gold_equivalent`` is valid only for synthetic fixtures because it is
    computed from the same explicit policy used to generate the fixture.  It is
    not a substitute for clinician adjudication in a controlled clinical study.
    """

    case_id: str
    category: str
    observed_a: PatientEyeEpisode
    observed_b: PatientEyeEpisode
    gold_equivalent: bool
