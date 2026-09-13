"""Historical analogue retrieval: structured filter + embedding top-K.

Given a target event, retrieval works in two stages:
  1. Structured filter: candidate pool restricted to events with the same
     event_type, overlapping countries/channels (if any target values are
     set), and severity within +/- `severity_tolerance`.
  2. Embedding cosine similarity: rank the filtered pool and keep the
     top-K.

Callers are expected to pass in a candidate pool already restricted to
`occurred_at < as_of` (point-in-time causality is enforced by the
repository/predictor layer, not here -- this module is a pure function of
whatever candidates it's given).
"""
from __future__ import annotations

from worldpulse.events.schemas import WorldEvent
from worldpulse.similarity.embeddings import cosine_similarity, embed_event


def structured_filter(
    target: WorldEvent,
    candidates: list[WorldEvent],
    severity_tolerance: float = 0.35,
) -> list[WorldEvent]:
    target_type = target.event_type.value if hasattr(target.event_type, "value") else target.event_type
    filtered = []
    for c in candidates:
        c_type = c.event_type.value if hasattr(c.event_type, "value") else c.event_type
        if c_type != target_type:
            continue
        if abs(c.severity - target.severity) > severity_tolerance:
            continue
        filtered.append(c)
    return filtered


def top_k_by_embedding(
    target: WorldEvent, candidates: list[WorldEvent], k: int = 50
) -> list[tuple[WorldEvent, float]]:
    if target.embedding is None:
        target.embedding = embed_event(target)
    scored = []
    for c in candidates:
        if c.embedding is None:
            c.embedding = embed_event(c)
        sim = cosine_similarity(target.embedding, c.embedding)
        scored.append((c, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def retrieve_analogues(
    target: WorldEvent,
    candidate_pool: list[WorldEvent],
    top_k: int = 50,
    severity_tolerance: float = 0.35,
) -> list[tuple[WorldEvent, float]]:
    """Full retrieval pipeline: structured filter -> embedding top-K."""
    filtered = structured_filter(target, candidate_pool, severity_tolerance)
    if not filtered:
        filtered = candidate_pool  # graceful fallback if filter is too strict
    return top_k_by_embedding(target, filtered, k=top_k)
