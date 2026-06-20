# V2 Pre-Submission and Public-Release Checklist

## Repository integrity

- [ ] `paper/V2.tex` and `paper/bibliography.bib` are the current manuscript sources; superseded material is clearly archived.
- [ ] `python -m compileall -q src tests` completes without error.
- [ ] `python -m pytest -q` passes.
- [ ] A seeded synthetic run writes `fixtures.jsonl`, `fixture_manifest.json`, `policy_manifest.json`, `pair_predictions.csv`, `audit_records.jsonl`, `metrics.json`, `ablation_summary.csv`, `environment.json`, `generated_table.tex`, and `run_manifest.json`.
- [ ] The run manifest records policy hash, fixture version, seed, command, dependency-lock hash, code commit, environment, and output hashes.
- [ ] No BioArc patient-level records, clinical notes, images, record-derived pairs, or controlled outputs are tracked.

## Manuscript integrity

- [ ] Every public metric is labelled as synthetic-policy-oracle or software-conformance evidence.
- [ ] No public claim reports clinical accuracy, safety, cohort size, completeness, latency, clinician agreement, or real-world ablation results.
- [ ] `Equivalent under Policy` is used for a single-policy `unsat` result; unqualified equivalence is not implied.
- [ ] The manuscript states that `recorded_treatment_token` is excluded from policy input at the index time.
- [ ] No LLM, multimodal embedding, or clinical knowledge-graph result is claimed without a released or governed implementation and matching run artifacts.

## Controlled-study gate

- [ ] A governed study has a locked phenotype, policy source/version, data version, index time, laterality policy, and patient-level split.
- [ ] A blinded clinician reference standard and adjudication protocol are documented.
- [ ] Statistical analysis is prespecified, including confidence intervals, exclusions, subgroup analysis, missingness, paired comparisons, and error taxonomy.
- [ ] Controlled input/output hashes and secure table-generation provenance are retained outside the public repository.
