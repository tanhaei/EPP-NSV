"""Seeded V2 synthetic patient--eye--episode fixture construction.

No fixture is sampled from a patient record or copied clinical note.  The suite
creates new schema-conformant values and explicit perturbations for every public
fixture family described in the manuscript.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from random import Random
from typing import Any

from .models import DiseaseFamily, Eye, PairCase, PatientEyeEpisode, Verdict
from .policy import DRDMEPolicy

FIXTURE_VERSION = "synthetic-fixture-suite-v2"
_INDEX_TIME = "2026-01-15"
_FACT_TIME = "2026-01-10"


def _critical_metadata(values: dict[str, Any], policy: DRDMEPolicy, episode_id: str) -> dict[str, dict[str, Any]]:
    source_by_field = {
        "dr_stage": "synthetic_fundus_module",
        "macular_edema": "synthetic_fundus_module",
        "centre_involvement": "synthetic_imaging_module",
        "fundus_neovascularization": "synthetic_fundus_module",
        "retinal_detachment": "synthetic_fundus_module",
        "active_ocular_infection": "synthetic_external_eye_module",
        "oct_available": "synthetic_imaging_module",
        "image_quality": "synthetic_imaging_module",
        "visual_acuity_band": "synthetic_vision_module",
        "symptom_trajectory": "synthetic_history_module",
        "functional_change_flag": "synthetic_history_module",
        "prior_retina_review": "synthetic_history_module",
        "prior_anti_vegf_state": "synthetic_history_module",
        "prior_laser_state": "synthetic_history_module",
        "followup_due_band": "synthetic_history_module",
    }
    assertion = {
        name: ("affirmed" if not isinstance(values[name], bool) or values[name] else "negated")
        for name in policy.critical_fields
    }
    return {
        "provenance": {name: source_by_field[name] for name in policy.critical_fields},
        "evidence_spans": {name: f"synthetic:{episode_id}:{name}" for name in policy.critical_fields},
        "assertion_status": assertion,
        "validation_status": {name: "fixture_validated" for name in policy.critical_fields},
        "field_observed_at": {name: _FACT_TIME for name in policy.critical_fields},
        "extraction_confidence": {name: 1.0 for name in policy.critical_fields},
    }


def _episode(rng: Random, index: int) -> PatientEyeEpisode:
    policy = DRDMEPolicy()
    stage = rng.choices(["MILD", "MODERATE", "SEVERE", "PDR"], weights=[35, 35, 20, 10], k=1)[0]
    macular_edema = rng.random() < {"MILD": 0.08, "MODERATE": 0.22, "SEVERE": 0.42, "PDR": 0.55}[stage]
    centre_involvement = macular_edema and rng.random() < 0.55
    values: dict[str, Any] = {
        "episode_id": f"EP-{index:05d}",
        "patient_id": f"PT-{index:05d}",
        "encounter_token": f"ENC-{index:05d}",
        "eye": Eye.OD if rng.random() < 0.5 else Eye.OS,
        "disease_family": DiseaseFamily.DR_DME,
        "observed_at": _INDEX_TIME,
        "age_years": rng.randint(30, 89),
        "sex": rng.choice(["F", "M"]),
        "hba1c": round(rng.uniform(5.5, 12.5), 1),
        "egfr": round(rng.uniform(25.0, 120.0), 1),
        "competing_pathology": False,
        "dr_stage": stage,
        "macular_edema": macular_edema,
        "centre_involvement": centre_involvement,
        "fundus_neovascularization": stage == "PDR" and rng.random() < 0.45,
        "retinal_detachment": False,
        "active_ocular_infection": False,
        "oct_available": True,
        "image_quality": "adequate",
        "visual_acuity_band": rng.choice(["A", "B", "C"]),
        "symptom_trajectory": rng.choice(["stable", "stable", "improving"]),
        "functional_change_flag": False,
        "prior_retina_review": rng.choice(["none", "documented"]),
        "prior_anti_vegf_state": rng.choice(["none", "historical"]),
        "prior_laser_state": "none",
        "followup_due_band": rng.choice(["not_due", "due"]),
        "recorded_treatment_token": None,
        "recorded_treatment_at": None,
        "clinical_note": "",
    }
    values.update(_critical_metadata(values, policy, values["episode_id"]))
    return PatientEyeEpisode(**values)


def _clone(episode: PatientEyeEpisode, suffix: str, **updates: object) -> PatientEyeEpisode:
    updates.setdefault("episode_id", f"{episode.episode_id}-{suffix}")
    updates.setdefault("patient_id", f"{episode.patient_id}-{suffix}")
    updates.setdefault("encounter_token", f"{episode.encounter_token}-{suffix}")
    return replace(episode, **updates)


def _metadata_without(episode: PatientEyeEpisode, field_name: str) -> dict[str, dict[str, Any]]:
    return {
        attribute: {key: value for key, value in dict(getattr(episode, attribute)).items() if key != field_name}
        for attribute in (
            "provenance",
            "evidence_spans",
            "assertion_status",
            "validation_status",
            "field_observed_at",
            "extraction_confidence",
        )
    }


def _near_miss(base: PatientEyeEpisode) -> PatientEyeEpisode:
    return _clone(
        base,
        "near-miss",
        retinal_detachment=True,
        macular_edema=False,
        centre_involvement=False,
        active_ocular_infection=False,
    )


def _branch(policy: DRDMEPolicy, episode: PatientEyeEpisode) -> str:
    return policy._profile_name(episode)


def build_pair_cases(n_pairs: int, seed: int = 7) -> list[PairCase]:
    """Create a balanced, deterministic V2 public fixture suite."""
    if n_pairs < 8:
        raise ValueError("n_pairs must be at least 8 to cover every V2 fixture family")
    rng = Random(seed)
    policy = DRDMEPolicy()
    cases: list[PairCase] = []
    categories = (
        "equivalent_demographic_shift",
        "policy_near_miss",
        "cross_eye_mismatch",
        "missing_critical_evidence",
        "stale_or_post_index_observation",
        "treatment_token_trap",
        "contradictory_evidence",
        "policy_version_perturbation",
    )

    for index in range(n_pairs):
        category = categories[index % len(categories)]
        a = _episode(rng, index * 10 + 1)
        a = _clone(a, "base", retinal_detachment=False, active_ocular_infection=False)
        b = a
        expected = Verdict.EQUIVALENT_UNDER_POLICY
        expected_branch = _branch(policy, a)
        variant_expected: Verdict | None = None

        if category == "equivalent_demographic_shift":
            b = _clone(
                a,
                "demographic",
                age_years=max(18, min(95, (a.age_years or 50) + rng.choice([-18, 14, 21]))),
                hba1c=round((a.hba1c or 7.0) + rng.uniform(-1.2, 1.2), 1),
                egfr=round(max(20.0, (a.egfr or 70.0) + rng.uniform(-20.0, 20.0)), 1),
            )

        elif category == "policy_near_miss":
            b = _near_miss(a)
            expected = Verdict.NON_EQUIVALENT
            expected_branch = "policy_near_miss"

        elif category == "cross_eye_mismatch":
            other_eye = Eye.OS if str(getattr(a.eye, "value", a.eye)) == "OD" else Eye.OD
            b = _clone(a, "other-eye", eye=other_eye)
            expected = Verdict.OUT_OF_SCOPE
            expected_branch = "same_eye_scope_gate"

        elif category == "missing_critical_evidence":
            metadata = _metadata_without(a, "macular_edema")
            b = _clone(a, "missing", macular_edema=None, clinical_note="", **metadata)
            expected = Verdict.INDETERMINATE
            expected_branch = "missingness_guard"

        elif category == "stale_or_post_index_observation":
            old_times = dict(a.field_observed_at)
            old_times["oct_available"] = "2025-09-01"
            b = _clone(a, "stale", field_observed_at=old_times)
            expected = Verdict.INDETERMINATE
            expected_branch = "temporal_guard"

        elif category == "treatment_token_trap":
            b = _clone(
                a,
                "token",
                recorded_treatment_token="synthetic_recorded_management_token",
                recorded_treatment_at="2026-01-16",
            )
            expected_branch = "treatment_token_excluded"

        elif category == "contradictory_evidence":
            validation = dict(a.validation_status)
            validation["macular_edema"] = "contradicted"
            b = _clone(a, "contradicted", validation_status=validation)
            expected = Verdict.INDETERMINATE
            expected_branch = "conflict_guard"

        elif category == "policy_version_perturbation":
            # Default policy distinguishes a non-centre macular state from monitoring.
            common = {
                "dr_stage": "MODERATE",
                "macular_edema": False,
                "centre_involvement": False,
                "fundus_neovascularization": False,
                "retinal_detachment": False,
                "active_ocular_infection": False,
                "visual_acuity_band": "A",
                "symptom_trajectory": "stable",
                "functional_change_flag": False,
                "prior_retina_review": "none",
                "prior_anti_vegf_state": "none",
                "prior_laser_state": "none",
                "followup_due_band": "not_due",
            }
            a = _clone(a, "version-a", **common)
            b = _clone(a, "version-b", macular_edema=True)
            expected = Verdict.NON_EQUIVALENT
            expected_branch = "default_non_centre_macular_branch"
            variant_expected = Verdict.EQUIVALENT_UNDER_POLICY

        cases.append(
            PairCase(
                case_id=f"PAIR-{index:05d}",
                category=category,
                observed_a=a,
                observed_b=b,
                expected_verdict=expected,
                expected_branch=expected_branch,
                policy_variant_expected_verdict=variant_expected,
            )
        )
    return cases


def episode_to_dict(episode: PatientEyeEpisode) -> dict[str, Any]:
    """JSON-safe serialisation for public synthetic fixture exports."""
    payload = asdict(episode)
    payload["eye"] = str(getattr(episode.eye, "value", episode.eye))
    payload["disease_family"] = str(getattr(episode.disease_family, "value", episode.disease_family))
    return payload
