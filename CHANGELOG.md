# Changelog

## Unreleased

### Independent-oracle and mutation testing

- Added `epp_nsv.independent_oracle.IndependentOracle`: a second, grammar-derived
  implementation of the pairwise verdict that shares no decision logic with
  `policy.py`/`verifier.py`, used to report non-self-referential agreement.
- Added `epp_nsv.mutation`: a mutation-testing harness that injects single-point
  policy faults (six classes) and scores kills through the real SMT-backed
  verifier against the seeded fixture suite. Mutant populations are enumerated
  from documented operator catalogues (emergent counts); mutant kills are
  measured at run time. No score is hardcoded.
- Added `epp-nsv-mutation` console script, `make mutation`, `docs/MUTATION_TESTING.md`,
  and `tests/test_mutation.py` (z3-free oracle tests plus a z3-guarded harness test).
- Note: the committed harness enumerates 64 mutants. If the manuscript mutation
  table reports a different population, regenerate the table from this harness;
  the committed code is the ground truth.

## 0.3.1 - 2026-06-21

### Terminology and verification boundary

- Renamed the public single-policy verdict from `Equivalent under Guideline` to `Equivalent under Policy`; the bundled DEMO-DRDME-v1 artifact is synthetic and is not a clinical guideline.
- Renamed the public policy interface field from `guideline_id` to `policy_id`.
- Clarified that SMT checks are concrete pairwise checks under fully bound fixture inputs, not universal model checking of a clinical state space.

## 0.2.0 - 2026-06-21

### Integrity and manuscript alignment

- Reframed the public package as a synthetic-verification and controlled-study reproducibility package.
- Added an explicit article--repository claim matrix, clinical-study protocol, semantic-lifting contract, release checklist, data guardrails, and schema-only templates.
- Clarified that the repository has no BioArc patient-level data, no real-data result bundle, no direct-LLM evaluation, no multimodal embedding evaluation, and no clinical-performance evidence.
- Updated the protocol-scope manuscript source with a repository citation, a code/data availability statement, figure/table cross-reference fixes, an `Out of scope` eligibility status, and a tracked workflow figure.

### Implementation

- Added explicit same-eye eligibility and `Out of scope` outcomes.
- Expanded state evidence metadata: provenance, evidence span, assertion, validation status, observation time, and confidence.
- Replaced output-constant SMT comparison with a policy-branch compiler that binds observed inputs and searches a Z3 decision-output counterexample.
- Added evidence-bearing deterministic fixture lifting; it is explicitly not an LLM implementation.
- Added controlled-study utilities: external pair-reference loading, optional Fleiss' kappa calculation, audit-oriented result files, and private policy-factory loading.
- Added a controlled-harness integration test and expanded unit coverage.

### Validation

- `python -m compileall -q src` passed.
- `PYTHONPATH=src python -m pytest -q` passed: 11 tests.
- Synthetic smoke run completed with 60 generated fixtures, seed 17.
