# Mutation Testing and Independent-Oracle Agreement

This document describes the `epp_nsv.mutation` harness, which operationalises the
manuscript's independent-oracle and mutation-testing study. Its purpose is to
break the **shared-specification circularity** of the fixture-conformance run:
the fixture contract and the verifier compile the same versioned policy, so the
full verifier cannot, by construction, fail its own contract. Mutation testing
and a second, non-shared oracle supply evidence that the verifier discriminates
correct from subtly incorrect policy logic.

## What the harness does

1. **Independent oracle.** `epp_nsv.independent_oracle.IndependentOracle` is a
   separate implementation of the pairwise verdict, written against the policy
   grammar in the manuscript appendix and sharing **no decision logic** with
   `policy.py`/`verifier.py` (only the typed data models are reused). The
   harness reports the fraction of fixtures on which the verifier and the
   oracle agree.
2. **Mutation testing.** The harness injects exactly one single-point fault into
   the *policy object* and re-runs the real (SMT-backed) verifier over the
   seeded fixture suite. A mutant is **killed** if the mutated verifier breaks
   the fixture contract on at least one pair — either a verdict that differs
   from the declared expected verdict, or an unsafe `Equivalent`/`Equivalent
   under Policy` verdict on a fixture that must abstain or be rejected.

## How the mutant population is constructed (emergent, not hardcoded)

Mutants are enumerated from explicit operator catalogues over the policy's own
fields and parameters (`build_mutants`). The per-class counts are therefore
reproducible and auditable; **no score is hardcoded** anywhere in the harness.

| Class | Construction | Count |
|---|---|---:|
| Negated scope or same-eye guard | drop disease gate, drop competing gate, drop same-eye gate, treat any pair as same-eye | 4 |
| Off-by-one temporal-window bound | `max_observation_age_days` offset by each of `-8..-1, +1..+8` | 16 |
| Relaxed laterality binding | treat unresolved laterality as resolved; drop pairwise laterality check | 2 |
| Dropped missingness branch | one mutant per critical field (drop its `missing:` guard) | 15 |
| Altered decision threshold | drop each reduced-vision band (C/D/E/REDUCED); ignore PDR / worsening / overdue; disable non-centre macular review | 8 |
| Provenance/validation check removed | drop provenance, evidence-span, assertion, confidence sub-checks; widen validation per critical field | 19 |
| **Total** | | **64** |

> **Important — mutant *kills* are measured at run time** by executing the
> verifier; only the mutant *population* above is fixed by the catalogue.

## Running it

```bash
make mutation
# or
python -m epp_nsv.mutation --n-pairs 64 --seed 17 --out-dir outputs/mutation_seed17
```

Outputs (same style as the rest of the public run bundle):

- `mutation_results.json` — per-class and overall counts, scores, survivors,
  independent-oracle agreement, and the policy hash.
- `mutation_results.csv` — flat per-class table.
- `mutation_results.tex` — a LaTeX table whose columns match the manuscript
  mutation-results table (Mutation class / Mutants / Killed / Mutation score).
- `mutation_detail.jsonl` — one line per mutant with its kill outcome.

## Integrity and manuscript reconciliation

The committed harness defines **64** mutants with the breakdown above. If the
manuscript table reports a different mutant population (for example, a
finer-grained per-field × per-operator enumeration), the two must be reconciled
**by regenerating the manuscript table from this committed harness** — the
committed code is the ground truth, never the reverse. Survivors reported under
the temporal and threshold classes localise fixture-suite sparsity (missing
boundary cases) rather than verifier unsoundness, and they directly specify the
boundary-targeted fixtures to add in the next release.
