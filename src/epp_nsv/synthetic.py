"""Privacy-safe synthetic patient-eye episode and pair construction.

The generator makes the article's pair categories executable: decision-equivalent
but demographically different pairs, near-miss counterfactuals, note-only
constraints, missingness cases, stale observations, and treatment-only traps.
"""

from __future__ import annotations

from dataclasses import replace
from random import Random

from .models import DiseaseFamily, Eye, PairCase, PatientEyeEpisode
from .policy import DRDMEPolicy


def _episode(rng: Random, index: int) -> PatientEyeEpisode:
    stage = rng.choices(
        ["MILD", "MODERATE", "SEVERE", "PDR"], weights=[35, 35, 20, 10], k=1
    )[0]
    edema_probability = {"MILD": 0.08, "MODERATE": 0.22, "SEVERE": 0.42, "PDR": 0.55}[stage]
    macular_edema = rng.random() < edema_probability
    neovascularization = stage == "PDR" and rng.random() < 0.45
    retinal_detachment = rng.random() < 0.015
    active_infection = rng.random() < 0.025
    anti_vegf_hold = macular_edema and rng.random() < 0.08
    eye = Eye.OD if rng.random() < 0.5 else Eye.OS
    note = ""
    if anti_vegf_hold:
        note = "Documented anti-VEGF held pending review."
    elif active_infection:
        note = "Active ocular infection documented."
    return PatientEyeEpisode(
        episode_id=f"EP-{index:05d}",
        patient_id=f"PT-{index:05d}",
        eye=eye,
        disease_family=DiseaseFamily.DR_DME,
        observed_at="2026-01-15",
        age_years=rng.randint(30, 89),
        sex=rng.choice(["F", "M"]),
        hba1c=round(rng.uniform(5.5, 12.5), 1),
        egfr=round(rng.uniform(25.0, 120.0), 1),
        dr_stage=stage,
        macular_edema=macular_edema,
        fundus_neovascularization=neovascularization,
        retinal_detachment=retinal_detachment,
        active_ocular_infection=active_infection,
        anti_vegf_hold=anti_vegf_hold,
        fundus_age_days=rng.randint(1, 75),
        clinical_note=note,
        provenance={
            "macular_edema": "fundus_module",
            "fundus_neovascularization": "fundus_module",
            "retinal_detachment": "fundus_module",
            "anti_vegf_hold": "treatment_panel",
        },
    )


def _clone(episode: PatientEyeEpisode, suffix: str, **updates: object) -> PatientEyeEpisode:
    updates.setdefault("episode_id", f"{episode.episode_id}-{suffix}")
    updates.setdefault("patient_id", f"{episode.patient_id}-{suffix}")
    return replace(episode, **updates)


def _gold_equivalent(a: PatientEyeEpisode, b: PatientEyeEpisode, policy: DRDMEPolicy) -> bool:
    return policy.decision(a) == policy.decision(b)


def _set_non_equivalent(base: PatientEyeEpisode, suffix: str) -> PatientEyeEpisode:
    """Change a decision-critical fact while retaining broadly similar features."""
    if not base.macular_edema:
        return _clone(base, suffix, macular_edema=True, anti_vegf_hold=False)
    if base.anti_vegf_hold:
        return _clone(base, suffix, anti_vegf_hold=False, clinical_note="")
    return _clone(base, suffix, anti_vegf_hold=True, clinical_note="Documented anti-VEGF held pending review.")


def build_pair_cases(n_pairs: int, seed: int = 7) -> list[PairCase]:
    """Generate labelled pairs with fully observed synthetic truth.

    Each category appears in rotation so every small smoke test has coverage.
    """
    if n_pairs < 6:
        raise ValueError("n_pairs must be at least 6 to cover each pair category")
    rng = Random(seed)
    policy = DRDMEPolicy()
    cases: list[PairCase] = []
    categories = (
        "equivalent_demographic_shift",
        "near_miss_counterfactual",
        "note_only_constraint",
        "missingness_safety_case",
        "stale_observation_case",
        "surface_match_trap",
    )

    for i in range(n_pairs):
        category = categories[i % len(categories)]
        truth_a = _episode(rng, i * 10 + 1)
        # Avoid rare detachment/infection in generic categories; reserve semantics.
        truth_a = _clone(
            truth_a,
            "truthA",
            retinal_detachment=False,
            active_ocular_infection=False,
        )
        truth_b = truth_a
        observed_a, observed_b = truth_a, truth_a

        if category == "equivalent_demographic_shift":
            truth_b = _clone(
                truth_a,
                "eq",
                age_years=max(18, min(95, (truth_a.age_years or 50) + rng.choice([-18, 14, 21]))),
                hba1c=round((truth_a.hba1c or 7.0) + rng.uniform(-1.2, 1.2), 1),
                egfr=round(max(20.0, (truth_a.egfr or 70.0) + rng.uniform(-20.0, 20.0)), 1),
            )
            observed_a, observed_b = truth_a, truth_b

        elif category == "near_miss_counterfactual":
            truth_b = _set_non_equivalent(truth_a, "counterfactual")
            observed_a, observed_b = truth_a, truth_b

        elif category == "note_only_constraint":
            # Both true states have a treatment hold. In observed data it is only
            # recoverable from an auditable note extractor.
            truth_a = _clone(
                truth_a,
                "noteA",
                macular_edema=True,
                anti_vegf_hold=True,
                clinical_note="Documented anti-VEGF held pending review.",
            )
            truth_b = _clone(
                truth_a,
                "noteB",
                age_years=max(18, (truth_a.age_years or 50) + 9),
            )
            observed_a = _clone(truth_a, "observed", anti_vegf_hold=None)
            observed_b = _clone(truth_b, "observed", anti_vegf_hold=None)

        elif category == "missingness_safety_case":
            truth_a = _clone(truth_a, "missingA", macular_edema=False, anti_vegf_hold=False)
            truth_b = _clone(truth_a, "missingB", macular_edema=True, anti_vegf_hold=False)
            # The key distinguishing condition is hidden in B; unsafe imputation
            # turns it into false and can make an unsupported equivalence claim.
            observed_a = truth_a
            observed_b = _clone(truth_b, "masked", macular_edema=None, clinical_note="")

        elif category == "stale_observation_case":
            truth_b = _set_non_equivalent(truth_a, "staleB")
            observed_a = truth_a
            observed_b = _clone(truth_b, "stale", fundus_age_days=180)

        elif category == "surface_match_trap":
            # Both outputs use retina_referral, but their full decision vectors
            # differ in safety constraints, tests, and follow-up windows.
            truth_a = _clone(
                truth_a,
                "pdr",
                dr_stage="PDR",
                macular_edema=False,
                fundus_neovascularization=False,
                retinal_detachment=False,
                active_ocular_infection=False,
                anti_vegf_hold=False,
            )
            truth_b = _clone(
                truth_a,
                "infection",
                dr_stage="MODERATE",
                active_ocular_infection=True,
                clinical_note="Active ocular infection documented.",
            )
            observed_a, observed_b = truth_a, truth_b

        gold = _gold_equivalent(truth_a, truth_b, policy)
        cases.append(
            PairCase(
                case_id=f"PAIR-{i:05d}",
                category=category,
                observed_a=observed_a,
                observed_b=observed_b,
                gold_equivalent=gold,
            )
        )

    return cases
