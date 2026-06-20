# Synthetic fixture release boundary

This directory intentionally contains documentation only. Generated public fixtures are emitted by `python -m epp_nsv.experiments` as `fixtures.jsonl` under the selected output directory.

The fixtures are fresh, seeded, schema-conformant synthetic patient--eye--episode records. They contain no BioArc patient-level data, real notes, images, or patient-derived pairs. Their expected labels are produced by the same versioned synthetic policy used by the verifier, so `fixture_conformance_rate` is a software-conformance measure only.
