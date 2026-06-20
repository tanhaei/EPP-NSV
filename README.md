# EPP-NSV: Public Reproducibility Package for Decision-Scoped Patient Equivalence

> **Similarity is not equivalence.** EPP-NSV is a research prototype for asking whether two **patient--eye--episode** states are indistinguishable under an explicit, versioned decision policy and observation model. It is not a diagnostic, triage, or treatment system.

## What this public repository establishes

| Evidence tier | Publicly reproducible here | Not established here |
|---|---|---|
| Software implementation | Typed state handling, disease/laterality scope gates, deterministic semantic-lifting fixtures, conservative missingness/temporal guards, policy compilation, SMT counterexample queries, audit records, unit tests. | Clinical safety or effectiveness. |
| Synthetic verification | Reproducible behavior against generated synthetic fixture labels, including ablations. | Performance on BioArc or any patient-level dataset. |
| Controlled clinical study | A private-run harness, input schemas, adjudication utilities, and release checklist. | A completed controlled study unless its approved private artifacts are produced and independently auditable. |

The repository contains **no BioArc patient-level data, real clinical notes, screenshots, re-identification keys, or real-data result bundle**. It must not be used to support numerical claims such as cohort size, clinician agreement, precision, coverage, latency, or ablation effects from a clinical dataset unless those results are produced in a governed environment and documented with an immutable run manifest.

Read [`docs/ARTICLE_ALIGNMENT.md`](docs/ARTICLE_ALIGNMENT.md) before citing this repository alongside a manuscript.

## What is implemented

- a typed **patient--eye--episode** state with laterality, timestamp, provenance, evidence span, assertion, validation status, confidence, and explicit missingness;
- a **DR/DME synthetic demonstration policy** with a same-eye and disease-scope gate;
- deterministic note lifting for synthetic fixtures, with an evidence-bearing contract for a future governed LLM adapter;
- a compiled **Z3 SMT distinguishing query** over policy branches, not merely a comparison of precomputed output constants;
- conservative verdicts: **Equivalent under Guideline**, **Non-equivalent**, **Indeterminate**, and **Out of scope**;
- synthetic fixture categories for demographic shifts, near misses, note-only constraints, missingness, stale observations, and treatment-token traps;
- a handcrafted similarity baseline and ablations;
- a controlled-study harness that accepts externally governed episode, pair-reference, and optional adjudication files;
- unit tests, smoke-test commands, data schemas, and a revision/release checklist.

## Important implementation boundaries

- The default policy identifier, `DEMO-DRDME-v1`, is a **synthetic test fixture**, not a clinical guideline.
- The default note extractor is **deterministic and rule-based**, not an LLM.
- The repository has no image modality or multimodal embedding model. Do not describe it as having evaluated multimodal embeddings unless an externally documented implementation and run are added.
- An `unsat` result means only that the two observed states are indistinguishable **under the encoded policy, input bindings, eligibility gate, and observation model**. It does not show that patients are clinically identical or interchangeable.
- The public package emits **Equivalent under Guideline** because it evaluates one named policy. An unqualified `Equivalent` verdict requires robust agreement across a documented approved policy set.

## Quick start: synthetic verification only

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m pytest -q
python -m epp_nsv.experiments --n-pairs 300 --seed 7 --out-dir outputs/experiment
```

Or:

```bash
make install
make test
make smoke
```

The generated bundle includes:

| File | Content | Permitted interpretation |
|---|---|---|
| `pair_predictions.csv` | Per-method synthetic predictions and reasons. | Fixture-level behavior only. |
| `metrics.json` | Precision/recall/coverage against a synthetic policy oracle. | Software validation only. |
| `run_metadata.json` | Scope, synthetic data declaration, policy ID, seed, and evidence boundary. | Audit record for the public run. |
| `ablation_summary.csv` | Synthetic ablation comparison. | Demonstration of expected fixture behavior only. |
| `report.md` | Human-readable synthetic-run summary. | Not a clinical result. |

## Controlled study harness

A real-data study must run outside this repository with approved access, a locked protocol, a policy approved for the study, and a clinician reference standard. The public package provides a harness; it does **not** provide the clinical study itself.

```bash
python -m epp_nsv.controlled \
  --episodes /secure/project/episodes.csv \
  --pairs /secure/project/pair_reference.csv \
  --policy-factory private_policy:build_policy \
  --adjudications /secure/project/adjudications.csv \
  --out-dir /secure/project/epp_run
```

The supplied policy factory must implement the documented EPP policy interface and must be locally reviewed. Do not commit inputs, policy secrets, clinical notes, raw adjudications, or output bundles containing protected information. See [`docs/CONTROLLED_STUDY.md`](docs/CONTROLLED_STUDY.md).

## Repository layout

```text
epp-nsv/
├── src/epp_nsv/              # State model, policy, lifting, SMT verifier, experiments
├── tests/                    # Unit and synthetic end-to-end tests
├── docs/                     # Scope, schemas, controlled-study protocol, release checklist
├── data/synthetic/           # Synthetic-data documentation only
├── data/governed/            # Empty guardrail directory; never commit controlled data
├── paper/                    # Protocol-scope manuscript source and alignment notes
├── scripts/run_smoke.sh      # Local synthetic smoke-test sequence
├── CITATION.cff
└── pyproject.toml
```

## Citation and manuscript alignment

Use `CITATION.cff` for this **software prototype**. The accompanying manuscript source in `paper/` is scoped as a methodological/protocol paper. A manuscript that reports real BioArc cohort counts, clinician adjudication, direct-LLM baselines, multimodal embedding results, or clinical performance requires the controlled-study artifacts identified in [`docs/ARTICLE_ALIGNMENT.md`](docs/ARTICLE_ALIGNMENT.md) and should not borrow the synthetic experiment results.

## Clinical safety and data governance

EPP-NSV is intended for retrospective research, audit, and methodological development. It is not validated for diagnosis, triage, treatment selection, or autonomous clinical use. Any future deployment requires local clinical validation, ethics approval where applicable, data-use agreements, security review, governance oversight, and monitoring.

## License

MIT. See [`LICENSE`](LICENSE).
