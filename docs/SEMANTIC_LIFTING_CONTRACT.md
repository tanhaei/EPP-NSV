# V2 Semantic-Lifting Contract

## Public prototype behaviour

The public repository uses a deterministic rule-based extractor only for synthetic note-like tokens. It is not an LLM and does not issue a verdict. A candidate must carry all of the following before it can become a policy input:

```text
field_name
schema-conformant value
evidence_span and character offsets
source_module
assertion
laterality
time_relation
observed_at or derivable pre-index time
validation_status
confidence
extractor_id
```

The public acceptance rule requires: the target field is currently missing; candidate laterality equals the episode laterality; time relation is `before_index`; assertion is admissible; source and validation are present; confidence is bounded; and the value is schema-conformant. Candidates failing this contract remain rejected audit evidence and cannot force a policy verdict.

## Governed adapters

A future LLM or clinical NLP adapter may only propose candidate facts under the same contract. It must never bypass validation, assert a decision, infer unresolved laterality without an approved rule, or turn a post-index treatment token into a policy feature. Any governed adapter requires an independently versioned implementation, secure evaluation protocol, and approved data handling.

## Public non-claim

This repository contains no direct-LLM baseline, no clinical-note corpus, no multimodal model, and no performance comparison between extractors.
