"""Minimal typed evidence graph used for V2 audit traces.

This lightweight graph is deliberately not presented as a clinical knowledge
graph.  It encodes only the public prototype's fact, source, predicate,
decision, support, contradiction, temporal, laterality, and dependency links.
"""

from __future__ import annotations

from typing import Any, Iterable

from .models import PatientEyeEpisode


def build_evidence_graph(
    episode: PatientEyeEpisode,
    *,
    critical_fields: Iterable[str],
    policy_id: str,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    episode_node = f"episode:{episode.episode_id}"
    nodes.append({"id": episode_node, "type": "episode", "eye": str(getattr(episode.eye, "value", episode.eye))})

    for field_name in critical_fields:
        fact_id = f"fact:{episode.episode_id}:{field_name}"
        source = episode.provenance.get(field_name)
        assertion = episode.assertion_status.get(field_name)
        validation = episode.validation_status.get(field_name)
        observed_at = episode.field_observed_at.get(field_name)
        nodes.append(
            {
                "id": fact_id,
                "type": "episode_fact",
                "field": field_name,
                "value": episode.field_value(field_name),
                "assertion": assertion,
                "validation": validation,
                "observed_at": observed_at,
                "eye": str(getattr(episode.eye, "value", episode.eye)),
            }
        )
        edges.append({"type": "binds_eye", "from": fact_id, "to": episode_node})
        if observed_at:
            time_id = f"time:{episode.episode_id}:{field_name}"
            nodes.append({"id": time_id, "type": "time", "value": observed_at})
            edges.append({"type": "precedes_or_equals_index", "from": time_id, "to": episode_node})
        if source:
            source_id = f"source:{episode.episode_id}:{field_name}"
            nodes.append({"id": source_id, "type": "source", "value": source})
            edges.append({"type": "support", "from": source_id, "to": fact_id})
        if str(assertion).lower() == "contradicted" or str(validation).lower() == "contradicted":
            edges.append({"type": "contradict", "from": fact_id, "to": episode_node})
        predicate_id = f"predicate:{policy_id}:{field_name}"
        nodes.append({"id": predicate_id, "type": "policy_predicate", "field": field_name})
        edges.append({"type": "depends_on", "from": fact_id, "to": predicate_id})

    for component in ("scope_status", "management_tier", "review_urgency_tier", "evidence_status"):
        decision_id = f"decision:{episode.episode_id}:{component}"
        nodes.append({"id": decision_id, "type": "decision_component", "field": component})
        edges.append({"type": "depends_on", "from": f"predicate:{policy_id}:dr_stage", "to": decision_id})

    return {"nodes": nodes, "edges": edges}
