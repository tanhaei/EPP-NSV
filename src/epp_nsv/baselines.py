"""Reproducible non-neural baselines for the experimental protocol."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .models import PatientEyeEpisode, Verdict, VerificationResult


@dataclass(frozen=True)
class SimilarityBaseline:
    """Handcrafted feature-distance baseline.

    It intentionally ignores provenance, temporal validity, and full decision
    semantics. This makes it useful for demonstrating why similarity is not a
    substitute for EPP, but it is not a clinical model.
    """

    threshold: float = 0.72

    def _vector(self, episode: PatientEyeEpisode) -> tuple[float, ...]:
        stage = {"MILD": 1.0, "MODERATE": 2.0, "SEVERE": 3.0, "PDR": 4.0}
        return (
            float(episode.age_years or 0) / 100.0,
            float(episode.hba1c or 0) / 15.0,
            float(episode.egfr or 0) / 150.0,
            stage.get(str(episode.dr_stage).upper(), 0.0) / 4.0,
            float(bool(episode.macular_edema)),
            float(bool(episode.fundus_neovascularization)),
            float(bool(episode.retinal_detachment)),
            float(bool(episode.active_ocular_infection)),
        )

    def verify(
        self,
        a: PatientEyeEpisode,
        b: PatientEyeEpisode,
    ) -> VerificationResult:
        if str(getattr(a.disease_family, "value", a.disease_family)) != str(
            getattr(b.disease_family, "value", b.disease_family)
        ) or str(getattr(a.eye, "value", a.eye)) != str(getattr(b.eye, "value", b.eye)):
            return VerificationResult(
                verdict=Verdict.OUT_OF_SCOPE,
                reasons=("baseline_scope_gate_failed",),
                solver_status="not_run",
                audit={"baseline": "handcrafted_similarity"},
            )
        va, vb = self._vector(a), self._vector(b)
        distance = sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))
        if distance <= self.threshold:
            verdict = Verdict.EQUIVALENT_UNDER_GUIDELINE
            reasons = (f"handcrafted_distance={distance:.4f}<=threshold",)
        else:
            verdict = Verdict.NON_EQUIVALENT
            reasons = (f"handcrafted_distance={distance:.4f}>threshold",)
        return VerificationResult(
            verdict=verdict,
            reasons=reasons,
            solver_status="not_run",
            audit={"baseline": "handcrafted_similarity", "distance": distance},
        )
