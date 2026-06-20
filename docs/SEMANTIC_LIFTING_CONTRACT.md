# Semantic-Lifting Contract

## Public prototype behavior

The repository's default `RuleBasedNoteExtractor` exists only for deterministic synthetic fixtures. It is **not an LLM**, not an NLP benchmark, and not evidence that the system can extract clinical facts from real notes.

## Governed adapter requirements

Any LLM or NLP extractor used in a controlled study must emit candidate facts rather than final clinical decisions. Every candidate must include:

```text
field_name
value
assertion
laterality / eye
observed_at or temporality relation
evidence span
source document identifier
extractor model and version
prompt/template version where applicable
confidence or calibrated uncertainty
```

A candidate may affect the verifier only after the study's validation policy checks that it:

1. maps to an allowed schema field and value type;
2. is grounded in retained source evidence;
3. has resolved or explicitly unresolved assertion, laterality, and time;
4. does not conflict with a higher-priority structured field without recorded adjudication;
5. is admissible at the index decision time;
6. is accepted by the study-specific evidence hierarchy.

If any condition fails, preserve the candidate for audit and return `Indeterminate` or request review. Do not hallucinate a completion, treat absence of extraction as absence of a finding, or let an LLM issue the final EPP verdict.

## Direct-LLM baseline

A direct-LLM baseline should be considered **not implemented** unless the repository or controlled release contains the exact model identifier, endpoint/version, prompt, decoding parameters, input packet, output parser, error policy, latency measurement definition, and privacy approval. A statement that direct LLM judgment was compared is an empirical claim and needs matched evaluation artifacts.
