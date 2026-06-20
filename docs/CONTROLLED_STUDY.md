# Controlled-Study Protocol and Private Evaluation Harness

## Scope

`python -m epp_nsv.controlled` is a secure, audit-oriented harness for a future governed study. It is not a clinical deployment tool and does not convert the bundled synthetic policy into a clinical guideline.

The public repository must remain free of patient-level records, free-text notes, screenshots, identifiers, raw adjudication labels, controlled audit files, and controlled outputs.

## Minimum controlled-study artifacts

| Artifact | Minimum content |
|---|---|
| Approved data version and cohort query | Access date, governance record, phenotype definition, and disclosure level. |
| `episodes.csv` | De-identified episode keys and the V2 schema. |
| `pair_reference.csv` | Pair IDs, episodes, and locked reference verdicts. |
| `adjudications.csv` | Secure individual labels and adjudicator pseudonyms, when agreement is evaluated. |
| Private policy module | Versioned, clinician-reviewed policy and observation contract. |
| Statistical analysis plan | Primary endpoint, exclusions, uncertainty method, subgroups, and baselines. |
| Secure run manifest | Input/output hashes, policy hash, code commit, environment, and table-generation provenance. |

## Episode input schema

The required header is:

```text
episode_id,patient_id,encounter_token,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,competing_pathology,dr_stage,macular_edema,centre_involvement,fundus_neovascularization,retinal_detachment,active_ocular_infection,oct_available,image_quality,visual_acuity_band,symptom_trajectory,functional_change_flag,prior_retina_review,prior_anti_vegf_state,prior_laser_state,followup_due_band,recorded_treatment_token,recorded_treatment_at,clinical_note
```

Optional JSON metadata fields are documented in `docs/DATA_SCHEMA.md`. Missing policy-critical values remain unknown and must not be silently negated.

## Pair and adjudication schemas

```text
pair_id,episode_a_id,episode_b_id,reference_verdict
```

```text
pair_id,adjudicator_id,verdict
```

Reference verdicts must use the public vocabulary: `Equivalent`, `Equivalent under Guideline`, `Non-equivalent`, `Indeterminate`, `Out of scope`, or `Verification failure`.

## Required controlled safeguards

- Split by de-identified **patient**, never by encounter or eye.
- Specify one primary endpoint: observed management concordance **or** policy-derived decision equivalence. Do not merge them.
- Fix the index-time, laterality, policy version, and observation contract before evaluation.
- Use blinded evidence packets and a documented adjudication process for any clinical reference standard.
- Report full denominators, exclusions, missingness, uncertainty intervals, paired comparisons, and error taxonomy.
- Preserve secure hashes and table-generation code; do not copy protected output into the public repository.

## Command

```bash
python -m epp_nsv.controlled \
  --episodes /secure/project/episodes.csv \
  --pairs /secure/project/pair_reference.csv \
  --policy-factory private_policy:build_policy \
  --adjudications /secure/project/adjudications.csv \
  --out-dir /secure/project/epp_run
```

The destination contains `controlled_predictions.csv`, `controlled_audit_records.jsonl`, `controlled_summary.json`, and `controlled_run_manifest.json`. All are secure artifacts, not public-release files.

## V2 private-policy factory contract

A private policy factory supplied through `--policy-factory package.module:callable` must return an object exposing the V2 verification contract: `guideline_id`, `critical_fields`, `domain_ok`, `pair_scope_issues`, `pair_observation_issues`, `observation_issues`, `fact_audit`, `decision`, `unsafe_impute_for_ablation`, `signature_fields`, `output_codebook`, `smt_output_expressions`, `decision_difference`, `policy_manifest`, and `policy_hash`. The runner rejects incomplete policies before reading a study output. The public demonstration policy is synthetic and must not be substituted for a governed clinical policy.
