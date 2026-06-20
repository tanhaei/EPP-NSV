# Article--Repository Alignment Matrix

## Purpose

This document prevents a public code repository from being cited as evidence for results it does not contain. It separates (1) claims supported by the public prototype, (2) claims that require a controlled, private research run, and (3) claims that must be removed or rewritten unless evidence is supplied.

## Non-negotiable integrity rule

A public repository containing synthetic fixtures cannot validate a claim about a real patient cohort merely because its schema resembles the intended clinical environment. Conversely, the absence of public patient data is appropriate when privacy restrictions apply; the evidence for real-data results must then be maintained in a governed, auditable location with enough non-sensitive artifacts for reviewers to assess the study.

## Claim matrix

| Manuscript claim | Public repository status | Evidence required before the claim may remain in a clinical-results paper |
|---|---|---|
| EPP defines decision-scoped, model-relative equivalence. | **Supported.** | Formal definition, policy version, code release tag. |
| The system uses patient--eye--episode units, laterality, timing, provenance, and missingness. | **Partially supported.** The public model and tests implement a minimal state abstraction. | Data dictionary, ETL code, schema mapping, and private validation report. |
| Scope is DR/DME and same-eye comparisons are required. | **Supported for the synthetic demonstration policy.** | Locked phenotype, code list, laterality resolution rule, and cohort flow diagram. |
| LLMs extract clinical facts/rules. | **Not supported as an empirical claim.** The public package has deterministic fixtures only. | Versioned model/provider, prompt, schema, source-span grounding, error analysis, privacy review, and clinician evaluation. |
| A knowledge graph grounds clinical relations. | **Schema-level only.** | Versioned ontology/graph artifact, rule mappings, coverage statistics, and error analysis. |
| SMT searches for a decision-distinguishing counterexample. | **Supported for the synthetic policy.** | Versioned policy compiler, solver version, formula/audit export, and consistency tests against the clinical policy. |
| A real BioArc extract contains a stated cohort size or data completeness. | **Not supported by this public package.** | Approved data-version identifier, frozen cohort query, exact cohort flow, secure run manifest, and institutional verification. |
| Three clinicians adjudicated pairs and achieved a stated Fleiss' kappa. | **Not supported by this public package.** Utilities are supplied, but no labels exist here. | Rater protocol, blinded packets, raw private labels, adjudication rules, exact kappa script/output, and declarations of rater qualifications. |
| Full EPP achieved a stated precision, coverage, latency, or safety result. | **Not supported by this public package.** | Frozen input pair list, reference standard, exact code/commit, policy version, environment, output hashes, and confidence intervals. |
| Direct LLM and multimodal embedding baselines were evaluated. | **Not supported.** | Reproducible baseline implementation, model/feature specification, prompts where applicable, and matched split/evaluation artifacts. |

## Two valid manuscript tracks

### Track S: public prototype / synthetic verification

This repository supports a paper that claims:

- a formalization and software prototype;
- synthetic fixture results validating implementation behavior;
- an interface and protocol for a future governed DR/DME study;
- no real BioArc data, patient-level data, or clinical-performance result.

Use evidence-bound language such as: *"The released experiments validate software behavior on constructed fixtures; they do not estimate clinical performance."*

### Track C: governed clinical evaluation

A clinical-results article may report BioArc findings only after all requirements below are satisfied:

1. Freeze the phenotype definition, index-time rule, laterality policy, eligibility criteria, and patient-level split before outcome analysis.
2. Version the data extract and record data-governance approval, access date, and allowed disclosure level.
3. Freeze the clinical decision target: observed clinician action **or** an approved policy-derived decision vector. Do not mix them as one primary endpoint.
4. Use a policy implementation reviewed by domain experts; record its source, version, jurisdiction/local applicability, and change log.
5. Create blinded evidence packets and a pre-specified adjudication protocol; retain raw labels securely.
6. Evaluate every reported baseline on the same pair set and patient-level split.
7. Report uncertainty: confidence intervals, denominator for every rate, exclusions, abstentions, and subgroup/missingness analysis.
8. Archive a non-sensitive run manifest containing code commit, dependency lock, policy hash, input/output hashes, and table-generation commands.
9. Ensure that all values in the paper tables are generated from the archived run, not typed manually.

## Claims that must not appear without private-study evidence

Do **not** report the following as completed facts unless the Track C evidence exists:

```text
- exact BioArc cohort size or coverage percentage;
- a DOI or data version that is a placeholder;
- clinician count, specialty, Fleiss' kappa, or adjudication details;
- precision, recall, coverage, latency, disagreement, or ablation numbers;
- direct-LLM results;
- multimodal embedding results;
- any claim that an SMT verdict proves real-world clinical interchangeability.
```

## Required citation boundary

The repository citation supports the software and synthetic fixtures only. A controlled BioArc study should additionally cite the approved data source according to its access agreement, but must not expose patient-level data or confidential identifiers in the public release.
