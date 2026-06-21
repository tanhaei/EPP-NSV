"""Tests for the independent oracle and the mutation-testing harness.

The independent-oracle tests are z3-free.  The full mutation run is skipped
automatically when ``z3`` is not installed, because the harness scores mutants
through the real (SMT-backed) verifier.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

import pytest

_BASE = pathlib.Path(__file__).resolve().parents[1] / "src" / "epp_nsv"


def _load_isolated(name: str):
    """Load a single module without importing the z3-dependent package __init__."""
    if "epp_nsv" not in sys.modules:
        pkg = types.ModuleType("epp_nsv")
        pkg.__path__ = [str(_BASE)]
        sys.modules["epp_nsv"] = pkg
    spec = importlib.util.spec_from_file_location(f"epp_nsv.{name}", _BASE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"epp_nsv.{name}"] = module
    spec.loader.exec_module(module)
    return module


_models = _load_isolated("models")
_oracle_mod = _load_isolated("independent_oracle")

from epp_nsv.models import DiseaseFamily, Eye, PatientEyeEpisode, Verdict  # noqa: E402
from epp_nsv.independent_oracle import IndependentOracle  # noqa: E402

_FIELDS = (
    "dr_stage", "macular_edema", "centre_involvement", "fundus_neovascularization",
    "retinal_detachment", "active_ocular_infection", "oct_available", "image_quality",
    "visual_acuity_band", "symptom_trajectory", "functional_change_flag",
    "prior_retina_review", "prior_anti_vegf_state", "prior_laser_state", "followup_due_band",
)
_VALS = dict(
    dr_stage="MODERATE", macular_edema=False, centre_involvement=False,
    fundus_neovascularization=False, retinal_detachment=False, active_ocular_infection=False,
    oct_available=True, image_quality="adequate", visual_acuity_band="A",
    symptom_trajectory="stable", functional_change_flag=False, prior_retina_review="none",
    prior_anti_vegf_state="none", prior_laser_state="none", followup_due_band="not_due",
)


def _meta() -> dict:
    return dict(
        provenance={f: "synthetic_fundus_module" for f in _FIELDS},
        evidence_spans={f: f"synthetic:{f}" for f in _FIELDS},
        assertion_status={f: "affirmed" for f in _FIELDS},
        validation_status={f: "fixture_validated" for f in _FIELDS},
        field_observed_at={f: "2026-01-10" for f in _FIELDS},
        extraction_confidence={f: 1.0 for f in _FIELDS},
    )


def _episode(eye: Eye = Eye.OD, **over) -> PatientEyeEpisode:
    values = dict(_VALS)
    values.update(over)
    return PatientEyeEpisode(
        episode_id="E", patient_id="P", eye=eye, disease_family=DiseaseFamily.DR_DME,
        observed_at="2026-01-15", competing_pathology=False, **values, **_meta(),
    )


def test_oracle_identical_pair_is_equivalent():
    oracle = IndependentOracle()
    assert oracle.verdict(_episode(), _episode()) == Verdict.EQUIVALENT_UNDER_POLICY


def test_oracle_cross_eye_is_out_of_scope():
    oracle = IndependentOracle()
    assert oracle.verdict(_episode(Eye.OD), _episode(Eye.OS)) == Verdict.OUT_OF_SCOPE


def test_oracle_missing_field_is_indeterminate():
    oracle = IndependentOracle()
    b = _episode().with_updates(macular_edema=None)
    assert oracle.verdict(_episode(), b) == Verdict.INDETERMINATE


def test_oracle_policy_relevant_change_is_non_equivalent():
    oracle = IndependentOracle()
    assert oracle.verdict(_episode(), _episode(retinal_detachment=True)) == Verdict.NON_EQUIVALENT


# --- full harness (requires z3) -------------------------------------------
def test_mutation_harness_runs_and_is_well_formed(tmp_path):
    pytest.importorskip("z3", reason="mutation harness scores mutants through the SMT verifier")
    from epp_nsv.mutation import CLASS_LABELS, build_mutants, run_mutation_study

    mutants = build_mutants()
    assert {m.mutation_class for m in mutants} == set(CLASS_LABELS)
    # every mutant id is unique
    assert len({m.mutant_id for m in mutants}) == len(mutants)

    summary = run_mutation_study(n_pairs=64, seed=17, out_dir=tmp_path)
    overall = summary["overall"]
    # the unmutated verifier must satisfy the contract, else kills are meaningless
    assert overall["base_contract_clean"] is True
    # mutant population is non-empty and scores are well-defined fractions
    assert overall["mutants"] == sum(row["mutants"] for row in summary["per_class"])
    assert 0 <= overall["killed"] <= overall["mutants"]
    # independent oracle should agree with the verifier on the synthetic suite
    assert overall["independent_oracle_agreement"] == 1.0
    # artifacts written
    for name in ("mutation_results.json", "mutation_results.csv", "mutation_results.tex", "mutation_detail.jsonl"):
        assert (tmp_path / name).exists()
