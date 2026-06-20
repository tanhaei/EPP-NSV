# V2 Synthetic Verification Protocol

## Objective

The public experiment measures exact agreement with a **synthetic-policy oracle**. It is software conformance testing, not clinical validation, model benchmarking on patients, or a treatment-effect study.

## Fixture families

1. `equivalent_demographic_shift`: a decision-irrelevant demographic change preserves the policy verdict.
2. `policy_near_miss`: a policy-relevant retinal perturbation yields a satisfiable counterexample.
3. `cross_eye_mismatch`: otherwise similar facts are attached to different eyes and the same-eye gate returns `Out of scope`.
4. `missing_critical_evidence`: a required fact is absent and the verifier returns `Indeterminate`.
5. `stale_or_post_index_observation`: a required fact lies outside the configured pre-index window and is rejected.
6. `treatment_token_trap`: a post-index recorded treatment token does not enter policy input or alter the verdict.
7. `contradictory_evidence`: a contradicted validation state yields `Indeterminate`.
8. `policy_version_perturbation`: a versioned synthetic branch change is recorded separately and may alter a verdict.

## Methods

- **Full EPP-NSV:** scope gate, laterality, missingness, temporal, provenance, policy compilation, SMT counterexample, and audit record.
- **Policy evaluator without counterexample query:** direct decision-vector comparison without an SMT distinction trace.
- **Guard ablations:** remove scope, laterality, temporal, missingness, or provenance validation one at a time.
- **Handcrafted similarity baseline:** feature overlap only; it has no policy-proof obligation.

## Run

```bash
python -m epp_nsv.experiments --n-pairs 64 --seed 17 --out-dir outputs/experiment
```

The run writes fixtures, fixture manifest, policy manifest/hash, predictions, audit records, metrics, ablation summary, policy-version comparison, environment record, report, generated LaTeX table commands, and `run_manifest.json` with output hashes.

## Measures and interpretation

The primary public measure is `fixture_conformance_rate`: the exact fraction of predicted verdicts matching the expected synthetic verdict. Additional checks report counterexample availability for expected non-equivalent fixtures, abstention correctness for expected indeterminate fixtures, scope safety for cross-eye fixtures, and unsafe-equivalence counts on guard fixtures.

Do not report these as clinical accuracy, precision, recall, coverage, safety, clinician agreement, latency, or BioArc performance.
