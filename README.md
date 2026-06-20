# EPP-NSV: Public Reproducibility Package for Decision-Scoped Patient--Eye--Episode Verification

> **Similarity is not equivalence.** EPP-NSV asks whether two synthetic patient--eye--episode states are indistinguishable under one explicit, versioned policy and observation model. It is a research-software prototype, not a diagnostic, triage, treatment-selection, or autonomous clinical system.

## Evidence boundary

| Tier | Publicly reproducible here | Not established here |
|---|---|---|
| Software implementation | Typed normalisation, evidence contracts, same-eye scope gate, temporal/provenance/missingness guards, deterministic synthetic lifting, policy compilation, SMT counterexample queries, typed evidence graphs, audits, and tests. | Clinical safety, treatment benefit, or real-patient interchangeability. |
| Synthetic verification | Exact conformance against a versioned synthetic-policy oracle, including deliberate guard ablations. | Performance on BioArc or any patient-level dataset. |
| Future controlled study | Private-run adapter, pair-reference utilities, controlled audit output, and run-manifest support. | A completed clinical study, unless its governed artifacts are produced and reviewed separately. |

The repository contains **no BioArc patient-level records, clinical notes, images, patient-derived pairs, re-identification keys, or controlled-study result bundle**. Synthetic fixtures are BioArc-informed only at the public schema and permitted aggregate-calibration-interface level.

## Implemented V2 contract

- a synthetic **patient--eye--episode** state with `OD`, `OS`, `OU`, and `UNK` laterality;
- a narrow, abstract DR/DME-inspired demonstration policy (`DEMO-DRDME-v1`), with a four-component decision vector: scope status, management tier, review-urgency tier, and evidence status;
- same-eye/disease scope gating, with unresolved laterality treated as **Indeterminate** rather than silently treated as negative or out-of-scope;
- required field-level provenance, evidence span, assertion, validation, observation time, confidence, and missingness semantics;
- explicit exclusion of `recorded_treatment_token` from policy inputs at the index time;
- a minimal typed evidence graph for fact, source, predicate, decision, support/contradiction, temporal, laterality, and dependency traces;
- deterministic, evidence-bearing synthetic note lifting only; no LLM is bundled or evaluated;
- compiled Z3 counterexample queries with `sat`, `unsat`, and conservative verification-failure handling;
- eight synthetic fixture families: demographic shifts, policy near misses, cross-eye mismatch, missing evidence, stale evidence, treatment-token traps, contradictory evidence, and policy-version perturbations;
- a run bundle containing fixtures, fixture manifest, policy manifest/hash, predictions, audit records, metrics, ablations, environment metadata, dependency-lock hash, generated table commands, and an integrity manifest.

## Quick start: synthetic software validation

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m pytest -q
python -m epp_nsv.experiments --n-pairs 64 --seed 17 --out-dir outputs/experiment
```

Or run:

```bash
make install
make test
make smoke
```

The bundle is **synthetic software-validation evidence only**:

| Artifact | Content | Permitted interpretation |
|---|---|---|
| `fixtures.jsonl` | Fresh constructed fixture inputs and expected synthetic verdicts. | Public schema/fixture inspection only. |
| `policy_manifest.json` | Policy ID, hash, observation model, and missingness contract. | Defines the model-relative comparison. |
| `pair_predictions.csv` | Expected synthetic verdict, predicted verdict, solver status, and reason. | Fixture conformance only. |
| `audit_records.jsonl` | Admissible/rejected facts, evidence graphs, scope trace, and counterexamples. | Traceability only. |
| `metrics.json` | Exact synthetic-fixture conformance and guard checks. | Not clinical performance. |
| `run_manifest.json` | Seed, command, environment, lock hash, commit, and artifact hashes. | Rerun and integrity audit. |
| `generated_table.tex` | Generated macros for synthetic-validation tables. | Never label as clinical results. |

## Controlled-study harness

A real-data study must run only in a governed environment with a locked phenotype, named data version, approved policy, patient-level partitioning, blinded reference standard, prespecified analysis plan, and local governance approval.

```bash
python -m epp_nsv.controlled \
  --episodes /secure/project/episodes.csv \
  --pairs /secure/project/pair_reference.csv \
  --policy-factory private_policy:build_policy \
  --adjudications /secure/project/adjudications.csv \
  --out-dir /secure/project/epp_run
```

The harness writes controlled predictions, audit records, a summary, and a secure-run manifest with input/output hashes. Do not commit any controlled input or output to this public repository.

## Repository layout

```text
epp-nsv/
├── src/epp_nsv/              # State, policy, lifting, evidence graph, SMT verifier, experiments
├── tests/                    # V2 unit and synthetic end-to-end tests
├── docs/                     # V2 schema, protocol, release and scope documentation
├── data/                     # Documentation/templates only; no patient data
├── requirements.lock         # Tested dependency lock for the release record
└── pyproject.toml
```

## Safety and citation boundary

Use `CITATION.cff` for the software prototype and cite the exact release tag or commit. A public `unsat` result means only that two inputs are indistinguishable under the encoded synthetic policy, observation model, and bindings. It does not establish clinical identity, clinical interchangeability, guideline validity, or safety in practice.
