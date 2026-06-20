# Synthetic EPP-NSV Software-Validation Run

- Fixture version: `synthetic-fixture-suite-v2`
- Pairs: `64`
- Seed: `17`
- Data: constructed synthetic fixtures only; no BioArc or patient-level data were used.
- Oracle: versioned synthetic policy; not clinician adjudication or clinical truth.
- Interpretation: software conformance and guard behaviour only; not clinical accuracy, safety, coverage, or treatment validity.

| Method | Fixture conformance | Witness availability | Indeterminate abstention | Scope safety |
|---|---:|---:|---:|---:|
| epp_nsv_full | 1.0 | 1.0 | 1.0 | 1.0 |
| policy_evaluator_without_counterexample_query | 1.0 | 0.0 | 1.0 | 1.0 |
| ablation_remove_scope_gate | 0.875 | 1.0 | 1.0 | 0.0 |
| ablation_collapse_laterality | 0.875 | 1.0 | 1.0 | 0.0 |
| ablation_remove_temporal_filter | 0.875 | 1.0 | 0.6667 | 1.0 |
| ablation_treat_missing_as_absent | 0.625 | 1.0 | 0.0 | 1.0 |
| ablation_remove_provenance_validation | 0.75 | 1.0 | 0.3333 | 1.0 |
| handcrafted_similarity_baseline | 0.5 | 0.0 | 0.0 | 0.0 |
