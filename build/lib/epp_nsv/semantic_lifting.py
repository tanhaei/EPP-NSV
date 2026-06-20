"""Evidence-bearing deterministic semantic lifting for synthetic fixtures only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any, Protocol, Sequence

from .models import PatientEyeEpisode


@dataclass(frozen=True)
class CandidateFact:
    """Untrusted candidate fact with the mandatory V2 acceptance contract."""

    field_name: str
    value: Any
    evidence_span: str
    span_start: int
    span_end: int
    source_module: str
    assertion: str
    eye: str | None
    time_relation: str
    observed_at: str | None
    validation_status: str
    confidence: float = 1.0
    extractor_id: str = "rule_based_synthetic_fixture_extractor"


class NoteConstraintExtractor(Protocol):
    def extract_candidates(self, note: str | None) -> Sequence[CandidateFact]:
        """Return evidence-bearing candidate facts, never verdicts."""


@dataclass(frozen=True)
class RuleBasedNoteExtractor:
    """Offline extractor for note-like synthetic fixture tokens, not an LLM."""

    def extract_candidates(self, note: str | None) -> tuple[CandidateFact, ...]:
        text = note or ""
        lower = text.lower()
        eye_match = re.search(r"\b(od|os|ou)\b", lower)
        eye = eye_match.group(1).upper() if eye_match else None
        before_index = "before index" in lower
        time_relation = "before_index" if before_index else "unknown"
        patterns: tuple[tuple[str, Any, str, str], ...] = (
            ("macular oedema present", True, "macular_edema", "affirmed"),
            ("macular edema present", True, "macular_edema", "affirmed"),
            ("centre involvement present", True, "centre_involvement", "affirmed"),
            ("center involvement present", True, "centre_involvement", "affirmed"),
            ("symptoms worsening", "worsening", "symptom_trajectory", "affirmed"),
        )
        candidates: list[CandidateFact] = []
        for phrase, value, field_name, assertion in patterns:
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
                    source_module="synthetic_note_module",
                    assertion=assertion,
                    eye=eye,
                    time_relation=time_relation,
                    observed_at=None,
                    validation_status="synthetic_fixture_accepted",
                )
            )
        return tuple(candidates)

    @staticmethod
    def _pre_index_date(index_time: str) -> str | None:
        try:
            return (date.fromisoformat(index_time[:10]) - timedelta(days=1)).isoformat()
        except ValueError:
            return None

    def apply(
        self,
        episode: PatientEyeEpisode,
    ) -> tuple[PatientEyeEpisode, dict[str, Any], tuple[CandidateFact, ...], tuple[CandidateFact, ...]]:
        """Accept only schema-valid, pre-index, same-eye candidates for empty fields."""
        candidates = self.extract_candidates(episode.clinical_note)
        accepted: list[CandidateFact] = []
        rejected: list[CandidateFact] = []
        updates: dict[str, Any] = {}
        episode_eye = str(getattr(episode.eye, "value", episode.eye))
        for candidate in candidates:
            valid = (
                episode.field_value(candidate.field_name) is None
                and candidate.eye == episode_eye
                and candidate.time_relation == "before_index"
                and candidate.assertion in {"affirmed", "negated"}
                and candidate.source_module != ""
                and candidate.validation_status == "synthetic_fixture_accepted"
                and 0.0 <= candidate.confidence <= 1.0
            )
            if valid:
                updates[candidate.field_name] = candidate.value
                accepted.append(candidate)
            else:
                rejected.append(candidate)
        if not updates:
            return episode, {}, tuple(), tuple(rejected)

        provenance = dict(episode.provenance)
        evidence_spans = dict(episode.evidence_spans)
        assertion_status = dict(episode.assertion_status)
        validation_status = dict(episode.validation_status)
        field_observed_at = dict(episode.field_observed_at)
        confidence = dict(episode.extraction_confidence)
        default_time = self._pre_index_date(episode.observed_at)
        for candidate in accepted:
            field_name = candidate.field_name
            provenance[field_name] = candidate.source_module
            evidence_spans[field_name] = candidate.evidence_span
            assertion_status[field_name] = candidate.assertion
            validation_status[field_name] = candidate.validation_status
            field_observed_at[field_name] = candidate.observed_at or default_time or episode.observed_at
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
        return updated, updates, tuple(accepted), tuple(rejected)
