# Changelog

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
