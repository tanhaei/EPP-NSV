# Validation Record — Release 0.3.0

## Validation environment

- Date: 2026-06-21
- Python: 3.13.5
- `z3-solver`: 4.16.0.0
- `pytest`: 9.1.1
- Dependency record: `requirements.lock`

## Commands executed

```bash
python -m compileall -q src tests
python -m pytest -q
python -m epp_nsv.experiments --n-pairs 64 --seed 17 --out-dir outputs/final_smoke
```

## Result boundary

- Compilation completed without error.
- Unit/integration suite passed: **16 tests**.
- The 64-pair seeded V2 synthetic run completed successfully.
- Full EPP-NSV exact fixture conformance was `1.0` for that deterministic release run.
- Expected missingness/staleness/contradiction fixtures abstained; cross-eye fixtures were out of scope; expected non-equivalent fixtures carried SMT counterexample traces.
- The run bundle contained fixtures, fixture manifest, policy manifest/hash, predictions, audits, metrics, ablation summary, policy-version comparison, environment metadata, generated table commands, and a run manifest with artifact hashes.

These are **synthetic-fixture software-validation results only**. They do not demonstrate clinical accuracy, clinician agreement, safety, coverage, latency, guideline validity, treatment validity, BioArc performance, or real-patient interchangeability. Repeat the commands and regenerate the manifest after any code, policy, fixture, or dependency change.
