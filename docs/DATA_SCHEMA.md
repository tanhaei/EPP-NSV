# EPP-NSV Research Schema

## Scope and evidence boundary

This schema supports a **research-only DR/DME demonstration policy** and a controlled-study adapter. It contains no BioArc data and does not establish the actual availability, coverage, coding standard, or quality of any institutional dataset. Every real-data ingestion must occur under the applicable ethics approval, data-use agreement, security controls, and de-identification process.

The canonical analysis unit is a **patient--eye--episode**, not a patient-wide vector. Every decision-relevant fact should retain laterality, observation time, source provenance, assertion status, validation status, and extraction confidence. A missing value is unknown, not a negative finding.

## Core EHR domains anticipated by the framework

| Domain | Typical fields | Potential role in EPP | Public-package status |
|---|---|---|---|
| Demographics | age, sex, encounter time | Cohort description and fairness audit; not a shortcut for equivalence. | Minimal fields represented. |
| Diagnoses / comorbidity | DR/DME phenotype, systemic conditions | Scope gate and policy preconditions. | Disease-family token only in default policy. |
| Procedures | imaging, injection, surgery, time line | Treatment history and pathway context. | Schema-level extension point. |
| Medications | agent, exposure, hold, adverse event | Decision/safety constraints. | `anti_vegf_hold` fixture only. |
| Labs / vitals | HbA1c, eGFR, creatinine, blood pressure | Potential policy constraints and temporal evidence. | Retained but unused by default policy. |
| Clinical notes | findings, laterality, negation, uncertainty | Candidate fact extraction with evidence provenance. | Deterministic synthetic-fixture extractor only. |
| Temporal order | source time and observation age | Excludes post-index or stale evidence. | Fundus-age guard implemented. |
| Outcomes | complication, follow-up, subsequent care | Secondary retrospective analysis; never proof of index equivalence. | Not implemented in default policy. |
| Research linkage | patient and episode pseudonyms | Episode construction and patient-level leakage control. | Minimal IDs represented. |

## Specialty-form abstraction

| Module | Example fields | Role in a future disease-specific policy |
|---|---|---|
| A. External Eye Exam | eyelid position, conjunctiva status, corneal surface, sclera change, ocular alignment | Surface pathology and alternate-pathway constraints. |
| B. Strabismus | deviation type/angle, laterality, fixation pattern, binocular function, gaze configuration | Strabismus decision tasks. |
| C. Anterior Segment + Angle | cornea, chamber depth, cells/flare, iris, lens opacity, angle status | Cataract, glaucoma, inflammation, and safety branches. |
| D. Fundus Exam | optic disc, macular oedema, vascular pattern, peripheral retina, tear/detachment | Primary synthetic DR/DME policy signal. |
| E. Treatment Panel | medical/surgical categories, referral, follow-up | Observable decision-output components. |

The public prototype does **not** assert that these are the exact fields, user interface, or controlled vocabulary of the BioArc system. A clinical study must supply a separately approved data dictionary and mapping document.

## Minimal executable CSV adapter

The adapter in `src/epp_nsv/normalization.py` requires:

```text
episode_id,patient_id,eye,disease_family,observed_at,age_years,sex,hba1c,egfr,
dr_stage,macular_edema,fundus_neovascularization,retinal_detachment,
active_ocular_infection,anti_vegf_hold,fundus_age_days,clinical_note
```

Optional JSON-object columns preserve audit metadata:

```text
provenance_json,evidence_spans_json,assertion_status_json,validation_status_json,
field_observed_at_json,extraction_confidence_json
```

Empty safety-critical cells remain `None`. The full verifier returns `Indeterminate` rather than treating them as absent.

## Decision-critical fields in the synthetic policy

`dr_stage`, `macular_edema`, `fundus_neovascularization`, `retinal_detachment`, `active_ocular_infection`, `anti_vegf_hold`, and `fundus_age_days`.

The default policy uses a **90-day fundus observation window** solely as a testable synthetic rule. A governed clinical study must replace it with a clinically approved policy, evidence hierarchy, temporal window, and change log.
