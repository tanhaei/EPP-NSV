# V2 Synthetic Patient--Eye--Episode Schema

## Scope and release boundary

This public schema represents **BioArc-informed synthetic fixtures**, not BioArc records. It captures specialty-form structure and evidence semantics required to test a narrow DR/DME-inspired demonstration policy. It does not assert an institutional data dictionary, cohort size, availability, completeness, terminology mapping, or outcome validity.

## Unit of analysis

A fixture state is a patient--eye--episode tuple with a synthetic patient key, synthetic episode key, encounter token, eye, index time, and field-level evidence metadata. Supported laterality values are `OD`, `OS`, `OU`, and `UNK`. `UNK` is unresolved evidence and yields an indeterminate result when laterality is required.

## Executable CSV adapter

`src/epp_nsv/normalization.py` requires this header:

```text
episode_id,patient_id,encounter_token,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,competing_pathology,dr_stage,macular_edema,centre_involvement,fundus_neovascularization,retinal_detachment,active_ocular_infection,oct_available,image_quality,visual_acuity_band,symptom_trajectory,functional_change_flag,prior_retina_review,prior_anti_vegf_state,prior_laser_state,followup_due_band,recorded_treatment_token,recorded_treatment_at,clinical_note
```

Optional JSON-object columns preserve the V2 evidence contract:

```text
provenance_json,evidence_spans_json,assertion_status_json,validation_status_json,field_observed_at_json,extraction_confidence_json
```

The adapter preserves an empty policy-critical cell as `None`. The full verifier then returns `Indeterminate`; it never treats absence as a negative finding.

## Policy-visible synthetic field groups

| Group | Representative fields | Role |
|---|---|---|
| Scope and identity | `disease_family`, `eye`, `observed_at`, `competing_pathology`, `encounter_token` | Establishes a valid patient--eye--episode comparison. |
| Retinal disease state | `dr_stage`, `fundus_neovascularization`, `retinal_detachment` | Drives abstract retinal and urgent-exception branches. |
| Macular and imaging state | `macular_edema`, `centre_involvement`, `oct_available`, `image_quality` | Determines whether an imaging-dependent synthetic branch is evaluable. |
| Visual function | `visual_acuity_band`, `symptom_trajectory`, `functional_change_flag` | Provides non-prescriptive review context. |
| Prior care history | `prior_retina_review`, `prior_anti_vegf_state`, `prior_laser_state`, `followup_due_band` | Encodes only pre-index history. |
| Evidence quality | metadata JSON fields | Controls provenance, validation, temporal admissibility, confidence, and conservative abstention. |
| Leakage trap | `recorded_treatment_token`, `recorded_treatment_at` | Kept for audit but excluded from policy inputs. |

## Observation contract

Every policy-critical fact must have a declared value, source, evidence-span token, assertion state, validation state, observation time, and confidence between 0 and 1. A fact is rejected when missing, stale, post-index, contradictory, unvalidated, unsupported, or otherwise malformed. The default synthetic observation window is 90 days solely to create testable fixtures; it is not a clinical recommendation.
