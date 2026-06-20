"""Simple non-clinical similarity baseline for the synthetic experiment."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .models import PatientEyeEpisode, Verdict, VerificationResult


@dataclass(frozen=True)
class SimilarityBaseline:
    """Feature-overlap baseline with no policy proof obligation.

    It intentionally does not enforce evidence provenance, temporal admissibility,
    or full policy semantics.  Its labels are experiment-internal comparison
    outputs, not clinical conclusions.
    """

    threshold: float = 0.62

    def _vector(self, episode: PatientEyeEpisode) -> tuple[float, ...]:
        stage = {"MILD": 1.0, "MODERATE": 2.0, "SEVERE": 3.0, "PDR": 4.0}
        vision = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0, "E": 5.0, "REDUCED": 4.0}
        return (
            float(episode.age_years or 0) / 100.0,
            float(episode.hba1c or 0) / 15.0,
            float(episode.egfr or 0) / 150.0,
            stage.get(str(episode.dr_stage).upper(), 0.0) / 4.0,
            float(bool(episode.macular_edema)),
            float(bool(episode.centre_involvement)),
            float(bool(episode.fundus_neovascularization)),
            float(bool(episode.retinal_detachment)),
            vision.get(str(episode.visual_acuity_band).upper(), 0.0) / 5.0,
            float(str(episode.symptom_trajectory).lower() == "worsening"),
        )

    def verify(self, a: PatientEyeEpisode, b: PatientEyeEpisode) -> VerificationResult:
        if str(getattr(a.disease_family, "value", a.disease_family)) != str(
            getattr(b.disease_family, "value", b.disease_family)
        ):
            return VerificationResult(
                verdict=Verdict.OUT_OF_SCOPE,
                reasons=("baseline_disease_scope_mismatch",),
                solver_status="not_run",
                audit={"baseline": "handcrafted_similarity"},
            )
        va, vb = self._vector(a), self._vector(b)
        distance = sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))
        if distance <= self.threshold:
            verdict = Verdict.EQUIVALENT_UNDER_POLICY
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
