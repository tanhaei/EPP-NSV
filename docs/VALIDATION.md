# Validation Record

## Validation environment

- Date: 2026-06-21
- Python: 3.13.5
- `z3-solver`: 4.16.0
- `pytest`: 9.0.2
- Test command: `PYTHONPATH=src python -m pytest -q`

## Commands executed

```bash
python -m compileall -q src
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m epp_nsv.experiments \
  --n-pairs 60 --seed 17 --out-dir outputs/smoke
```

A minimal controlled-harness integration run was also executed with two locally created synthetic-like rows and the bundled **demonstration** policy factory. No patient-level or BioArc data were accessed in validation.

## Result

- `compileall`: completed without error.
- Unit/integration suite: **11 passed**.
- Synthetic smoke experiment: **60 generated patient-pair fixtures**, seed `17`, completed successfully.
- Generated artifacts: `pair_predictions.csv`, `metrics.json`, `run_metadata.json`, `ablation_summary.csv`, and `report.md`.
- Controlled-harness smoke check: wrote `controlled_predictions.csv` and `controlled_summary.json` from a temporary, non-clinical CSV input.

## Synthetic smoke-run checks

| Measure | Value |
|---|---:|
| Coverage | 0.6667 |
| Indeterminate rate | 0.3333 |
| Equivalence precision | 1.0000 |
| Non-equivalence precision | 1.0000 |
| Unsafe equivalence rate | 0.0000 |
| Similarity--equivalence disagreement | 0.0500 |

These values are **synthetic-fixture software-validation outputs**. They must not be reported as BioArc findings, clinician agreement, clinical performance, guideline validity, or patient-safety estimates. Re-run the commands after any code, dependency, or policy change; update this record with the exact environment and output hashes for a tagged release.
