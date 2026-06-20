# Pre-Submission and Public-Release Checklist

## Repository integrity

- [ ] `python -m pytest -q` passes in a clean environment.
- [ ] `./scripts/run_smoke.sh` completes and the generated output is marked synthetic only.
- [ ] No file under the public repository contains patient data, clinical note text, identifiers, raw labels, screenshots, or restricted data-derived values.
- [ ] `.gitignore` excludes data, outputs, virtual environments, and private policy modules.
- [ ] `README.md`, `CITATION.cff`, package version, manuscript version, and release tag agree.
- [ ] Every public claim has a traceable code path, test, or artifact.
- [ ] The repository contains no placeholders such as `TBD`, `10.xxxx`, `<commit>`, or invented performance values in release-facing documents.

## Manuscript integrity

- [ ] The manuscript clearly states whether it is a **synthetic prototype paper** or a **governed clinical evaluation**.
- [ ] The abstract, introduction, tables, conclusion, and data-availability statement use the same evidence boundary.
- [ ] Every table and figure is cited in the text before or near its first appearance.
- [ ] Every table value is reproducible from a frozen run; no values are manually typed.
- [ ] Every baseline listed in the paper is implemented and evaluated on the same split, or is removed.
- [ ] The manuscript does not call deterministic fixture lifting an LLM evaluation.
- [ ] The manuscript does not claim multimodal embeddings or image analysis unless those artifacts are implemented and evaluated.
- [ ] SMT wording is model-relative: proof applies to the encoded policy and observation model only.

## Clinical-evaluation gate

- [ ] Data access, ethics, and DUA requirements are documented and valid for the reported study.
- [ ] A data version, cohort query, phenotype, laterality policy, and index time are locked before analysis.
- [ ] The primary target is explicit: observed clinician action **or** policy-derived decision vector.
- [ ] A policy source/version/local applicability statement is approved by domain experts.
- [ ] Pair construction and patient-level train/validation/test separation are documented.
- [ ] Adjudication is blinded where appropriate; rater qualifications, consensus process, and agreement statistics are reproducible.
- [ ] Confidence intervals, exclusions, missingness, coverage, abstention, and subgroup analyses are reported.
- [ ] Non-sensitive run metadata and output hashes are archived.
