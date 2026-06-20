# Changelog

## 0.3.0 - 2026-06-21

### V2 manuscript alignment

- Replaced the current manuscript source with `paper/V2.tex`; moved V1 manuscript and workflow material to `paper/archive/`.
- Replaced the repository bibliography with the V2 bibliography supplied for the current manuscript.
- Reframed the public implementation around the V2 abstract decision vector: scope status, management tier, review-urgency tier, and evidence status.
- Removed clinical-looking policy outputs and direct treatment-selection semantics from the executable demonstration policy.

### Evidence and safety contract

- Added `UNK` laterality and corrected unresolved laterality handling to `Indeterminate` rather than `Out of scope`.
- Added V2 fields for competing pathology, centre involvement, imaging/quality, visual function, prior care, follow-up status, encounter linkage, and post-index treatment-token traps.
- Added provenance, evidence-span, assertion, validation, field-time, and confidence enforcement to the observation model.
- Added typed evidence-graph traces and explicit admissible/rejected fact audit records.
- Added explicit exclusion of `recorded_treatment_token` from policy inputs.

### Fixtures, experiments, and reproducibility

- Replaced the older six-category fixture suite with eight V2 fixture families, including cross-eye, contradictory-evidence, treatment-token, and policy-version cases.
- Replaced public precision/recall-style reporting with exact synthetic fixture conformance and guard-behaviour checks.
- Added fixture exports, policy manifests/hashes, audit JSONL, environment metadata, dependency-lock hashing, generated LaTeX table commands, output hashes, and V2 run manifests.
- Added controlled-run audit records and secure controlled manifests with input/output hashes.

### Validation

- `python -m compileall -q src tests` completed successfully.
- `python -m pytest -q` passed: 16 tests.
- Seeded V2 synthetic smoke validation completed with 64 fixtures and full verifier conformance of 1.0 against the synthetic oracle.

## 0.2.0 - 2026-06-21

Superseded by release 0.3.0. The historical record is retained only for provenance.
