"""A versioned synthetic DR/DME policy used to exercise EPP-NSV.

This module is not a clinical guideline and must not direct care.  It exists to
make the formal EPP distinction between a policy decision, an observation model,
and an SMT distinguishing query executable in public, privacy-safe fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from z3 import ArithRef, BoolRef, If, Or

from .models import DecisionVector, DiseaseFamily, PatientEyeEpisode


@dataclass(frozen=True)
class DRDMEPolicy:
    """Synthetic, named decision semantics for a DR/DME case study.

    The output follows the manuscript's decision vector: urgency, management
    domain, treatment class, safety constraints, follow-up, referral, and
    required tests.  Every label is a pedagogical policy token, not a medical
    recommendation.  A governed real-world study must supply a separately
    versioned and clinically approved policy implementation.
    """

    guideline_id: str = "DEMO-DRDME-v1"
    max_fundus_age_days: int = 90

    @property
    def critical_fields(self) -> tuple[str, ...]:
        return (
            "dr_stage",
            "macular_edema",
            "fundus_neovascularization",
            "retinal_detachment",
            "active_ocular_infection",
            "anti_vegf_hold",
            "fundus_age_days",
        )

    @staticmethod
    def _enum_value(value: object) -> str:
        return str(getattr(value, "value", value))

    def domain_ok(self, episode: PatientEyeEpisode) -> bool:
        return self._enum_value(episode.disease_family) == DiseaseFamily.DR_DME.value

    def pair_scope_issues(
        self,
        a: PatientEyeEpisode,
        b: PatientEyeEpisode,
    ) -> list[str]:
        """Apply the public prototype's disease and same-eye eligibility gate."""
        issues: list[str] = []
        if not self.domain_ok(a) or not self.domain_ok(b):
            issues.append("disease_scope_not_supported_by_named_policy")
        eye_a, eye_b = self._enum_value(a.eye), self._enum_value(b.eye)
        if eye_a not in {"OD", "OS", "OU"} or eye_b not in {"OD", "OS", "OU"}:
            issues.append("unresolved_or_unsupported_laterality")
        elif eye_a != eye_b:
            issues.append(f"incompatible_laterality:{eye_a}!={eye_b}")
        return issues

    def observation_issues(
        self,
        episode: PatientEyeEpisode,
        *,
        enforce_temporal: bool = True,
    ) -> list[str]:
        issues: list[str] = []
        for field_name in self.critical_fields:
            if episode.field_value(field_name) is None:
                issues.append(f"missing:{field_name}")
        if (
            enforce_temporal
            and episode.fundus_age_days is not None
            and episode.fundus_age_days > self.max_fundus_age_days
        ):
            issues.append(
                f"stale:fundus_age_days={episode.fundus_age_days}>"
                f"{self.max_fundus_age_days}"
            )
        return issues

    @staticmethod
    def _profiles() -> dict[str, DecisionVector]:
        """The only output profiles permitted by the synthetic policy."""
        return {
            "retinal_detachment": DecisionVector(
                urgency="emergency",
                management_domain="vitreoretinal",
                treatment_class="surgical_pathway",
                safety_constraints=("retinal_detachment",),
                follow_up_window="same_day",
                referral="retina_service",
                required_tests=("dilated_fundus_exam", "retinal_imaging"),
            ),
            "ocular_infection": DecisionVector(
                urgency="urgent",
                management_domain="vitreoretinal",
                treatment_class="retina_referral",
                safety_constraints=("active_ocular_infection",),
                follow_up_window="same_day",
                referral="retina_service",
                required_tests=("dilated_fundus_exam", "infection_assessment"),
            ),
            "proliferative_or_neovascular": DecisionVector(
                urgency="urgent",
                management_domain="vitreoretinal",
                treatment_class="retina_referral",
                safety_constraints=(),
                follow_up_window="14_days",
                referral="retina_service",
                required_tests=("oct", "dilated_fundus_exam"),
            ),
            "macular_edema_hold": DecisionVector(
                urgency="urgent",
                management_domain="vitreoretinal",
                treatment_class="medical_review",
                safety_constraints=("documented_anti_vegf_hold",),
                follow_up_window="14_days",
                referral="retina_service",
                required_tests=("oct", "dilated_fundus_exam"),
            ),
            "macular_edema": DecisionVector(
                urgency="routine",
                management_domain="vitreoretinal",
                treatment_class="anti_vegf_candidate",
                safety_constraints=(),
                follow_up_window="30_days",
                referral="retina_service",
                required_tests=("oct", "dilated_fundus_exam"),
            ),
            "observation": DecisionVector(
                urgency="routine",
                management_domain="vitreoretinal",
                treatment_class="observation",
                safety_constraints=(),
                follow_up_window="90_days",
                referral="ophthalmology_follow_up",
                required_tests=("fundus_photo",),
            ),
        }

    def _profile_name(self, episode: PatientEyeEpisode) -> str:
        """Select a policy branch for a complete synthetic state."""
        if bool(episode.retinal_detachment):
            return "retinal_detachment"
        if bool(episode.active_ocular_infection):
            return "ocular_infection"
        if str(episode.dr_stage).upper() == "PDR" or bool(
            episode.fundus_neovascularization
        ):
            return "proliferative_or_neovascular"
        if bool(episode.macular_edema) and bool(episode.anti_vegf_hold):
            return "macular_edema_hold"
        if bool(episode.macular_edema):
            return "macular_edema"
        return "observation"

    def decision(self, episode: PatientEyeEpisode) -> DecisionVector:
        """Evaluate the synthetic policy on a complete state."""
        missing = self.observation_issues(episode, enforce_temporal=False)
        if missing:
            raise ValueError(
                "Cannot evaluate a complete decision vector with missing fields: "
                + ", ".join(missing)
            )
        return self._profiles()[self._profile_name(episode)]

    def output_codebook(self) -> dict[str, dict[str, int]]:
        """Build deterministic per-field encodings for Z3 output expressions."""
        codebook: dict[str, dict[str, int]] = {}
        for field_name in self.signature_fields():
            values = {
                repr(profile.as_mapping()[field_name])
                for profile in self._profiles().values()
            }
            codebook[field_name] = {
                value: index for index, value in enumerate(sorted(values))
            }
        return codebook

    def smt_output_expressions(
        self,
        *,
        retinal_detachment: BoolRef,
        active_ocular_infection: BoolRef,
        stage_is_pdr: BoolRef,
        fundus_neovascularization: BoolRef,
        macular_edema: BoolRef,
        anti_vegf_hold: BoolRef,
        codebook: Mapping[str, Mapping[str, int]],
    ) -> dict[str, ArithRef]:
        """Compile the synthetic policy branches into Z3 expressions.

        Inputs are symbolic Booleans; the verifier binds them to the observed
        complete state and asks Z3 whether any decision-output component can
        differ.  This is structurally different from merely pinning two Python
        output vectors and comparing constants.
        """
        profiles = self._profiles()
        pdr_or_neo = Or(stage_is_pdr, fundus_neovascularization)
        branches = (
            (retinal_detachment, "retinal_detachment"),
            (active_ocular_infection, "ocular_infection"),
            (pdr_or_neo, "proliferative_or_neovascular"),
            (macular_edema & anti_vegf_hold, "macular_edema_hold"),
            (macular_edema, "macular_edema"),
        )

        expressions: dict[str, ArithRef] = {}
        for field_name in self.signature_fields():
            fallback = codebook[field_name][
                repr(profiles["observation"].as_mapping()[field_name])
            ]
            expression: ArithRef = If(
                branches[-1][0],
                codebook[field_name][
                    repr(profiles[branches[-1][1]].as_mapping()[field_name])
                ],
                fallback,
            )
            for condition, profile_name in reversed(branches[:-1]):
                expression = If(
                    condition,
                    codebook[field_name][
                        repr(profiles[profile_name].as_mapping()[field_name])
                    ],
                    expression,
                )
            expressions[field_name] = expression
        return expressions

    def unsafe_impute_for_ablation(self, episode: PatientEyeEpisode) -> PatientEyeEpisode:
        """Unsafe completion used only to demonstrate the missingness ablation."""
        defaults = {
            "dr_stage": "MILD",
            "macular_edema": False,
            "fundus_neovascularization": False,
            "retinal_detachment": False,
            "active_ocular_infection": False,
            "anti_vegf_hold": False,
            "fundus_age_days": 0,
        }
        updates = {
            name: default
            for name, default in defaults.items()
            if episode.field_value(name) is None
        }
        return episode.with_updates(**updates) if updates else episode

    def signature_fields(self) -> tuple[str, ...]:
        return tuple(DecisionVector.__dataclass_fields__.keys())

    @staticmethod
    def decision_difference(
        a: DecisionVector,
        b: DecisionVector,
        fields: Iterable[str] | None = None,
    ) -> list[str]:
        names = tuple(fields) if fields is not None else tuple(a.as_mapping())
        differences: list[str] = []
        a_map, b_map = a.as_mapping(), b.as_mapping()
        for name in names:
            if a_map[name] != b_map[name]:
                differences.append(f"{name}: {a_map[name]!r} != {b_map[name]!r}")
        return differences
