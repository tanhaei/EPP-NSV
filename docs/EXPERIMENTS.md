# Synthetic Verification Protocol

The public experiment is a **software-verification exercise using generated fixtures**. It does not analyze BioArc data, real patient data, clinical notes, imaging, or clinician-adjudicated labels. It must not be interpreted as a clinical evaluation.

## Implemented research proxies

| Question | Executable synthetic proxy | Not demonstrated |
|---|---|---|
| Similarity vs. decision equivalence | Handcrafted feature-distance baseline compared with EPP. | Performance of learned or multimodal embeddings. |
| Distant but decision-equivalent pairs | `equivalent_demographic_shift` fixtures vary non-decision fields. | Demographic fairness or real clinical generalization. |
| Close but non-equivalent pairs | `near_miss_counterfactual` and `surface_match_trap` fixtures change policy-critical facts. | Rates in clinical populations. |
| Conservative abstention | Missingness and stale-fundus fixtures must return `Indeterminate`. | Clinical safety improvement. |
| Sensitivity to design choices | Ablations remove missingness, temporal checks, fixture lifting, or full-vector verification. | Causal importance of components in real workflows. |

## Fixture categories

1. `equivalent_demographic_shift`: non-decision variation with the same synthetic decision vector.
2. `near_miss_counterfactual`: one policy-critical change.
3. `note_only_constraint`: a fact recoverable from a deterministic fixture extractor.
4. `missingness_safety_case`: a differentiating fact is unknown; full EPP must abstain.
5. `stale_observation_case`: evidence is older than the synthetic observation window; full EPP must abstain.
6. `surface_match_trap`: treatment token matches but another decision-vector component differs.

## Methods

- `epp_nsv_full`: disease and laterality gate + deterministic fixture lifting + missingness/temporal guards + compiled Z3 full-decision query.
- `ablation_no_missingness_guard`: unsafe default-value completion for demonstration.
- `ablation_no_temporal_guard`: accepts stale observations.
- `ablation_no_semantic_lifting`: cannot recover note-only fixture constraints.
- `ablation_no_smt_full_vector`: compares treatment class only.
- `handcrafted_similarity_baseline`: non-neural feature-distance baseline.

A direct LLM baseline and a multimodal embedding baseline are **not implemented**. Reporting either requires a separately versioned implementation and a matched evaluation artifact.

## Run

```bash
python -m epp_nsv.experiments --n-pairs 300 --seed 7 --out-dir outputs/experiment
```

The command writes:

- `pair_predictions.csv`: one row per method and synthetic pair;
- `metrics.json`: synthetic-oracle precision, recall, abstention, coverage, and disagreement;
- `run_metadata.json`: scope and evidence-boundary declaration;
- `ablation_summary.csv`: compact synthetic comparison;
- `report.md`: human-readable synthetic-run summary.

## Interpretation

A passing run validates expected software behavior, artifact generation, and conservative guard behavior. It does **not** estimate guideline validity, clinician acceptance, clinical effectiveness, patient safety, fairness, or BioArc performance. A controlled study requires the protocol in [`CONTROLLED_STUDY.md`](CONTROLLED_STUDY.md).
