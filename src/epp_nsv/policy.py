"""Versioned, non-prescriptive synthetic DR/DME demonstration policy.

This module operationalises the V2 manuscript's abstract decision vector.  It
is a policy fixture for software verification only; it is neither a clinical
practice guideline nor a treatment-selection system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from typing import Any, Iterable, Mapping

from z3 import ArithRef, BoolRef, If, Or

from .models import DecisionVector, DiseaseFamily, Eye, PatientEyeEpisode


@dataclass(frozen=True)
class DRDMEPolicy:
    """Frozen synthetic policy and observation contract used by the public suite."""

    policy_id: str = "DEMO-DRDME-v1"
    rule_version: str = "v2-synthetic-1"
    max_observation_age_days: int = 90
    non_centre_macular_requires_review: bool = True

    @property
    def critical_fields(self) -> tuple[str, ...]:
        return (
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

    @staticmethod
    def _enum_value(value: object) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    def domain_ok(self, episode: PatientEyeEpisode) -> bool:
        return self._enum_value(episode.disease_family) == DiseaseFamily.DR_DME.value

    def pair_scope_issues(
        self,
        a: PatientEyeEpisode,
        b: PatientEyeEpisode,
        *,
        enforce_laterality: bool = True,
    ) -> list[str]:
        """Return genuine scope failures, not unresolved-evidence failures."""
        issues: list[str] = []
        if not self.domain_ok(a) or not self.domain_ok(b):
            issues.append("disease_scope_not_supported_by_named_policy")
        if a.competing_pathology is True or b.competing_pathology is True:
            issues.append("competing_pathology_not_supported_by_named_policy")
        if enforce_laterality:
            eye_a, eye_b = self._enum_value(a.eye), self._enum_value(b.eye)
            # UNK is evidence insufficiency and is handled conservatively later.
            if eye_a != Eye.UNK.value and eye_b != Eye.UNK.value and eye_a != eye_b:
                issues.append(f"incompatible_laterality:{eye_a}!={eye_b}")
        return issues

    def pair_observation_issues(self, a: PatientEyeEpisode, b: PatientEyeEpisode) -> list[str]:
        issues: list[str] = []
        for prefix, episode in (("A", a), ("B", b)):
            eye = self._enum_value(episode.eye)
            if eye == Eye.UNK.value or eye not in {member.value for member in Eye}:
                issues.append(f"{prefix}:unresolved_laterality")
            if episode.competing_pathology is None:
                issues.append(f"{prefix}:missing:competing_pathology")
        return issues

    def observation_issues(
        self,
        episode: PatientEyeEpisode,
        *,
        enforce_temporal: bool = True,
        enforce_provenance_validation: bool = True,
    ) -> list[str]:
        """Evaluate missingness, temporal, provenance, and validation guards."""
        issues: list[str] = []
        index_date = self._parse_date(episode.observed_at)
        if index_date is None:
            return ["invalid:index_time"]

        for field_name in self.critical_fields:
            value = episode.field_value(field_name)
            if value is None:
                issues.append(f"missing:{field_name}")
                continue

            if field_name == "image_quality" and str(value).lower() not in {"adequate", "good"}:
                issues.append(f"invalid:image_quality={value}")

            if not enforce_provenance_validation:
                continue

            source = str(episode.provenance.get(field_name, "")).strip()
            span = str(episode.evidence_spans.get(field_name, "")).strip()
            assertion = str(episode.assertion_status.get(field_name, "")).strip().lower()
            validation = str(episode.validation_status.get(field_name, "")).strip().lower()
            observed_value = episode.field_observed_at.get(field_name)
            confidence = episode.extraction_confidence.get(field_name)

            if not source:
                issues.append(f"missing_provenance:{field_name}")
            if not span:
                issues.append(f"missing_evidence_span:{field_name}")
            if assertion in {"", "uncertain", "contradicted"}:
                issues.append(f"invalid_assertion:{field_name}={assertion or 'missing'}")
            if validation not in {
                "fixture_validated",
                "synthetic_fixture_accepted",
                "governed_validated",
            }:
                issues.append(f"invalid_validation:{field_name}={validation or 'missing'}")
            if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
                issues.append(f"invalid_confidence:{field_name}")

            fact_date = self._parse_date(str(observed_value) if observed_value else None)
            if fact_date is None:
                issues.append(f"invalid_or_missing_fact_time:{field_name}")
            elif enforce_temporal:
                if fact_date > index_date:
                    issues.append(f"post_index:{field_name}")
                elif (index_date - fact_date).days > self.max_observation_age_days:
                    issues.append(f"stale:{field_name}")

        return issues

    def fact_audit(
        self,
        episode: PatientEyeEpisode,
        *,
        enforce_temporal: bool,
        enforce_provenance_validation: bool,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return policy-admissible and rejected facts for the audit record."""
        issues = self.observation_issues(
            episode,
            enforce_temporal=enforce_temporal,
            enforce_provenance_validation=enforce_provenance_validation,
        )
        issues_by_field: dict[str, list[str]] = {}
        for issue in issues:
            field = issue.split(":", 1)[-1].split("=", 1)[0]
            issues_by_field.setdefault(field, []).append(issue)

        admissible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for field_name in self.critical_fields:
            fact = {
                "field": field_name,
                "value": episode.field_value(field_name),
                "source": episode.provenance.get(field_name),
                "evidence_span": episode.evidence_spans.get(field_name),
                "assertion": episode.assertion_status.get(field_name),
                "validation": episode.validation_status.get(field_name),
                "observed_at": episode.field_observed_at.get(field_name),
                "confidence": episode.extraction_confidence.get(field_name),
                "eye": self._enum_value(episode.eye),
            }
            field_issues = [item for item in issues if field_name in item]
            if field_issues:
                rejected.append(fact | {"reasons": field_issues})
            else:
                admissible.append(fact)

        if episode.recorded_treatment_token:
            rejected.append(
                {
                    "field": "recorded_treatment_token",
                    "value": episode.recorded_treatment_token,
                    "observed_at": episode.recorded_treatment_at,
                    "reasons": ["excluded_treatment_token_not_a_policy_input"],
                }
            )
        return admissible, rejected

    def _profiles(self) -> dict[str, DecisionVector]:
        """Abstract decision profiles; none encodes a treatment recommendation."""
        return {
            "retinal_urgent_exception": DecisionVector("in_scope", "urgent_exception", "immediate", "sufficient"),
            "infection_urgent_exception": DecisionVector("in_scope", "urgent_exception", "same_day", "sufficient"),
            "advanced_retinal_review": DecisionVector("in_scope", "advanced_retinal_review", "expedited", "sufficient"),
            "macular_escalated_review": DecisionVector("in_scope", "macular_review", "expedited", "sufficient"),
            "macular_history_review": DecisionVector("in_scope", "macular_review_with_history", "scheduled", "sufficient"),
            "macular_structured_review": DecisionVector("in_scope", "macular_review", "scheduled", "sufficient"),
            "functional_followup_review": DecisionVector("in_scope", "followup_review", "scheduled", "sufficient"),
            "monitoring": DecisionVector("in_scope", "monitoring", "routine", "sufficient"),
        }

    def _has_prior_care(self, episode: PatientEyeEpisode) -> bool:
        return any(
            str(value).lower() not in {"", "none", "no", "not_documented"}
            for value in (
                episode.prior_retina_review,
                episode.prior_anti_vegf_state,
                episode.prior_laser_state,
            )
        )

    def _profile_name(self, episode: PatientEyeEpisode) -> str:
        """Select a branch only after the observation model has accepted input."""
        if bool(episode.retinal_detachment):
            return "retinal_urgent_exception"
        if bool(episode.active_ocular_infection):
            return "infection_urgent_exception"
        if str(episode.dr_stage).upper() == "PDR" or bool(episode.fundus_neovascularization):
            return "advanced_retinal_review"
        reduced_vision = str(episode.visual_acuity_band).upper() in {"C", "D", "E", "REDUCED"}
        worsening = str(episode.symptom_trajectory).lower() == "worsening"
        overdue = str(episode.followup_due_band).lower() == "overdue"
        if bool(episode.macular_edema):
            if bool(episode.centre_involvement) or reduced_vision or worsening or overdue:
                return "macular_escalated_review"
            if self._has_prior_care(episode):
                return "macular_history_review"
            if self.non_centre_macular_requires_review:
                return "macular_structured_review"
        if bool(episode.functional_change_flag) or overdue:
            return "functional_followup_review"
        return "monitoring"

    def decision(
        self,
        episode: PatientEyeEpisode,
        *,
        enforce_temporal: bool = True,
        enforce_provenance_validation: bool = True,
    ) -> DecisionVector:
        """Evaluate a complete, admissible synthetic state."""
        issues = self.observation_issues(
            episode,
            enforce_temporal=enforce_temporal,
            enforce_provenance_validation=enforce_provenance_validation,
        )
        if issues:
            raise ValueError("Cannot evaluate decision vector with unresolved evidence: " + ", ".join(issues))
        return self._profiles()[self._profile_name(episode)]

    def signature_fields(self) -> tuple[str, ...]:
        return tuple(DecisionVector.__dataclass_fields__)

    def output_codebook(self) -> dict[str, dict[str, int]]:
        codebook: dict[str, dict[str, int]] = {}
        for field_name in self.signature_fields():
            values = {repr(profile.as_mapping()[field_name]) for profile in self._profiles().values()}
            codebook[field_name] = {value: index for index, value in enumerate(sorted(values))}
        return codebook

    def smt_output_expressions(
        self,
        *,
        retinal_detachment: BoolRef,
        active_ocular_infection: BoolRef,
        stage_is_pdr: BoolRef,
        fundus_neovascularization: BoolRef,
        macular_edema: BoolRef,
        centre_involvement: BoolRef,
        reduced_vision: BoolRef,
        worsening_symptoms: BoolRef,
        functional_change: BoolRef,
        followup_overdue: BoolRef,
        has_prior_care: BoolRef,
        codebook: Mapping[str, Mapping[str, int]],
    ) -> dict[str, ArithRef]:
        """Compile abstract policy branches into symbolic decision expressions."""
        profiles = self._profiles()
        advanced = Or(stage_is_pdr, fundus_neovascularization)
        macular_escalated = macular_edema & Or(
            centre_involvement, reduced_vision, worsening_symptoms, followup_overdue
        )
        branches: list[tuple[BoolRef, str]] = [
            (retinal_detachment, "retinal_urgent_exception"),
            (active_ocular_infection, "infection_urgent_exception"),
            (advanced, "advanced_retinal_review"),
            (macular_escalated, "macular_escalated_review"),
            (macular_edema & has_prior_care, "macular_history_review"),
        ]
        if self.non_centre_macular_requires_review:
            branches.append((macular_edema, "macular_structured_review"))
        branches.append((Or(functional_change, followup_overdue), "functional_followup_review"))

        expressions: dict[str, ArithRef] = {}
        for field_name in self.signature_fields():
            expression: ArithRef = codebook[field_name][repr(profiles["monitoring"].as_mapping()[field_name])]
            for condition, profile_name in reversed(branches):
                expression = If(
                    condition,
                    codebook[field_name][repr(profiles[profile_name].as_mapping()[field_name])],
                    expression,
                )
            expressions[field_name] = expression
        return expressions

    def unsafe_impute_for_ablation(self, episode: PatientEyeEpisode) -> PatientEyeEpisode:
        """Unsafe completion used only to expose the missingness-guard failure."""
        defaults: dict[str, Any] = {
            "competing_pathology": False,
            "dr_stage": "MILD",
            "macular_edema": False,
            "centre_involvement": False,
            "fundus_neovascularization": False,
            "retinal_detachment": False,
            "active_ocular_infection": False,
            "oct_available": True,
            "image_quality": "adequate",
            "visual_acuity_band": "A",
            "symptom_trajectory": "stable",
            "functional_change_flag": False,
            "prior_retina_review": "none",
            "prior_anti_vegf_state": "none",
            "prior_laser_state": "none",
            "followup_due_band": "not_due",
        }
        updates = {name: value for name, value in defaults.items() if episode.field_value(name) is None}
        if self._enum_value(episode.eye) == Eye.UNK.value:
            updates["eye"] = Eye.OD
        return episode.with_updates(**updates)

    @staticmethod
    def decision_difference(
        a: DecisionVector,
        b: DecisionVector,
        fields: Iterable[str] | None = None,
    ) -> list[str]:
        names = tuple(fields) if fields is not None else tuple(a.as_mapping())
        a_map, b_map = a.as_mapping(), b.as_mapping()
        return [f"{name}: {a_map[name]!r} != {b_map[name]!r}" for name in names if a_map[name] != b_map[name]]

    def policy_manifest(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "rule_version": self.rule_version,
            "synthetic_only": True,
            "decision_vector": list(self.signature_fields()),
            "critical_fields": list(self.critical_fields),
            "observation_model": {
                "max_observation_age_days": self.max_observation_age_days,
                "requires_provenance": True,
                "requires_validation": True,
                "requires_pre_index_observation": True,
                "excludes_recorded_treatment_token": True,
            },
            "missingness_contract": "required unresolved evidence yields Indeterminate",
            "non_centre_macular_requires_review": self.non_centre_macular_requires_review,
        }

    def policy_hash(self) -> str:
        payload = json.dumps(self.policy_manifest(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
