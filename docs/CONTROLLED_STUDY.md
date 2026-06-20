# Controlled-Study Protocol and Private Evaluation Harness

## Scope

`python -m epp_nsv.controlled` is an **audit-oriented private-run harness**. It is not a clinical deployment system and does not convert the bundled synthetic policy into a guideline. It accepts externally governed, de-identified inputs only after an approved policy factory is supplied by the study team.

The public repository must remain free of patient-level records, free-text notes, screenshots, identifiers, raw adjudication labels, and controlled run outputs that could breach a data-use agreement.

## Minimum study artifacts

A credible clinical evaluation requires the following artifacts, stored under the access controls approved for the study rather than in this public repository:

| Artifact | Minimum content | Purpose |
|---|---|---|
| `episodes.csv` | De-identified episode keys and the documented input schema. | Reconstructs state inputs. |
| `pair_reference.csv` | Pair IDs, two episode IDs, and a locked reference verdict. | Defines the evaluation set. |
| `adjudications.csv` | Pair ID, adjudicator pseudonym, individual verdict. | Computes agreement and preserves adjudication trace. |
| Private policy module | A versioned, clinician-approved policy factory implementing the EPP interface. | Defines the decision vector and scope. |
| Run manifest | Data version, eligibility query hash, policy hash, code commit, environment, output hashes. | Makes tables auditable. |
| Statistical analysis plan | Primary endpoint, exclusions, uncertainty method, subgroups, and baseline definitions. | Prevents post hoc metric selection. |

## Episode input schema

The required CSV header is:

```text
episode_id,patient_id,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,
dr_stage,macular_edema,fundus_neovascularization,retinal_detachment,
active_ocular_infection,anti_vegf_hold,fundus_age_days,clinical_note
```

The following optional JSON-object columns preserve field-level audit metadata:

```text
provenance_json,evidence_spans_json,assertion_status_json,validation_status_json,
field_observed_at_json,extraction_confidence_json
```

An empty safety-critical value remains unknown. The full verifier returns `Indeterminate`; it must never silently transform an empty cell into a negative finding.

## Pair reference schema

```text
pair_id,episode_a_id,episode_b_id,reference_verdict
```

`reference_verdict` must be one of:

```text
Equivalent
Equivalent under Guideline
Non-equivalent
Indeterminate
Out of scope
```

A clinical manuscript should define whether `Equivalent` and `Equivalent under Guideline` are collapsed for its primary binary endpoint. The public harness records its binary-metric exclusion rule in `controlled_summary.json`; it does not make that scientific choice for the study.

## Adjudication schema

```text
pair_id,adjudicator_id,verdict
```

The helper computes Fleiss' kappa only if every evaluated pair has the same number of ratings. It cannot substitute for blinded review, a pre-specified consensus process, clinical qualifications, or a protocol explaining the decision task.

## Private policy factory

The `--policy-factory` argument uses `package.module:callable` syntax. The callable must return a policy object with:

```text
guideline_id
domain_ok(episode)
pair_scope_issues(episode_a, episode_b)
observation_issues(episode, enforce_temporal=True)
decision(episode)
unsafe_impute_for_ablation(episode)
signature_fields()
output_codebook()
smt_output_expressions(...)
```

The policy should be versioned, reviewed, and locked before final evaluation. It must record its source, clinical applicability, policy date, local adaptations, and all safety-critical predicates. Do not use the bundled `DEMO-DRDME-v1` policy for patient care or as the primary policy in a clinical-results manuscript.

## Command

```bash
python -m epp_nsv.controlled \
  --episodes /secure/project/episodes.csv \
  --pairs /secure/project/pair_reference.csv \
  --policy-factory private_policy:build_policy \
  --adjudications /secure/project/adjudications.csv \
  --out-dir /secure/project/epp_run
```

The command writes `controlled_predictions.csv` and `controlled_summary.json`. Before any result is reported, record a cryptographic hash of every input and output, the repository commit, Python and solver versions, policy hash, and the statistical-analysis script.

## Mandatory reporting safeguards

- Split by de-identified patient, not by encounter or eye, to prevent longitudinal leakage.
- Report the full denominator and all exclusions, including out-of-scope pairs and indeterminate cases.
- Distinguish observed clinician actions from policy-derived target actions.
- Do not use post-index facts as decision preconditions.
- Do not infer laterality where it cannot be resolved by the approved rule.
- Report missingness by feature and subgroup where permitted.
- Calculate confidence intervals for all principal performance estimates.
- Do not characterize `unsat` as proof of patient interchangeability beyond the encoded policy and observation model.
