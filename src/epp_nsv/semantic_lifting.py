"""Auditable semantic-lifting interfaces.

The paper permits an LLM to *propose* structured constraints.  The public
package deliberately does not ship or evaluate an external LLM.  Its offline
synthetic tests use deterministic rules, but the same evidence contract can be
implemented by a governed LLM adapter in a private environment.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, Sequence

from .models import PatientEyeEpisode


@dataclass(frozen=True)
class CandidateFact:
    """A candidate fact before policy-level acceptance.

    A clinical deployment must preserve the evidence span, assertion status,
    laterality, time, extractor identity, and confidence.  A candidate is not a
    verified patient fact merely because an extractor returned it.
    """

    field_name: str
    value: bool
    evidence_span: str
    span_start: int
    span_end: int
    assertion: str = "present"
    eye: str | None = None
    observed_at: str | None = None
    confidence: float = 1.0
    extractor_id: str = "rule_based_note_extractor"


class NoteConstraintExtractor(Protocol):
    """Protocol for schema-conformant candidate-fact extractors."""

    def extract_candidates(self, note: str | None) -> Sequence[CandidateFact]:
        """Return candidate facts with evidence suitable for audit."""


@dataclass(frozen=True)
class RuleBasedNoteExtractor:
    """Deterministic extractor used only for synthetic note fixtures.

    This is not an LLM and must not be presented as one.  It exists so the
    public test suite can validate the acceptance boundary for note-derived
    evidence without an external endpoint or protected text.
    """

    def extract_candidates(self, note: str | None) -> tuple[CandidateFact, ...]:
        text = note or ""
        lower = text.lower()
        patterns: tuple[tuple[str, bool, str], ...] = (
            ("no anti-vegf hold", False, "anti_vegf_hold"),
            ("no anti vegf hold", False, "anti_vegf_hold"),
            ("anti-vegf held", True, "anti_vegf_hold"),
            ("anti vegf held", True, "anti_vegf_hold"),
            ("active ocular infection", True, "active_ocular_infection"),
            ("retinal detachment", True, "retinal_detachment"),
        )
        candidates: list[CandidateFact] = []
        for phrase, value, field_name in patterns:
            match = re.search(re.escape(phrase), lower)
            if match is None:
                continue
            candidates.append(
                CandidateFact(
                    field_name=field_name,
                    value=value,
                    evidence_span=text[match.start() : match.end()],
                    span_start=match.start(),
                    span_end=match.end(),
                )
            )
        return tuple(candidates)

    def apply(
        self, episode: PatientEyeEpisode
    ) -> tuple[PatientEyeEpisode, dict[str, bool], tuple[CandidateFact, ...]]:
        """Accept only non-conflicting candidates for currently missing fields."""
        candidates = self.extract_candidates(episode.clinical_note)
        updates: dict[str, bool] = {}
        accepted: list[CandidateFact] = []
        for candidate in candidates:
            if episode.field_value(candidate.field_name) is None:
                updates[candidate.field_name] = candidate.value
                accepted.append(candidate)
        if not updates:
            return episode, {}, tuple()

        provenance = dict(episode.provenance)
        evidence_spans = dict(episode.evidence_spans)
        assertion_status = dict(episode.assertion_status)
        validation_status = dict(episode.validation_status)
        field_observed_at = dict(episode.field_observed_at)
        confidence = dict(episode.extraction_confidence)
        for candidate in accepted:
            field_name = candidate.field_name
            provenance[field_name] = candidate.extractor_id
            evidence_spans[field_name] = candidate.evidence_span
            assertion_status[field_name] = candidate.assertion
            validation_status[field_name] = "synthetic_fixture_accepted"
            field_observed_at[field_name] = candidate.observed_at or episode.observed_at
            confidence[field_name] = candidate.confidence
        updated = episode.with_updates(
            **updates,
            provenance=provenance,
            evidence_spans=evidence_spans,
            assertion_status=assertion_status,
            validation_status=validation_status,
            field_observed_at=field_observed_at,
            extraction_confidence=confidence,
        )
        return updated, updates, tuple(accepted)
