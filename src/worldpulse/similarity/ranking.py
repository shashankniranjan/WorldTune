"""Weighted re-ranking of retrieved historical analogues.

final_score = 0.5*embedding_similarity + 0.2*event_type_match
            + 0.1*geo_similarity + 0.1*severity_similarity
            + 0.1*channel_similarity
"""
from __future__ import annotations

from worldpulse.events.schemas import WorldEvent


def _event_type_match(a: WorldEvent, b: WorldEvent) -> float:
    a_type = a.event_type.value if hasattr(a.event_type, "value") else a.event_type
    b_type = b.event_type.value if hasattr(b.event_type, "value") else b.event_type
    return 1.0 if a_type == b_type else 0.0


def _geo_similarity(a: WorldEvent, b: WorldEvent) -> float:
    set_a, set_b = set(a.countries), set(b.countries)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _severity_similarity(a: WorldEvent, b: WorldEvent) -> float:
    return max(0.0, 1.0 - abs(a.severity - b.severity))


def _channel_similarity(a: WorldEvent, b: WorldEvent) -> float:
    set_a, set_b = set(a.affected_channels), set(b.affected_channels)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def rerank(
    target: WorldEvent, scored_candidates: list[tuple[WorldEvent, float]]
) -> list[tuple[WorldEvent, float]]:
    """Re-rank (candidate, embedding_similarity) pairs by the weighted formula."""
    reranked = []
    for candidate, emb_sim in scored_candidates:
        score = (
            0.5 * emb_sim
            + 0.2 * _event_type_match(target, candidate)
            + 0.1 * _geo_similarity(target, candidate)
            + 0.1 * _severity_similarity(target, candidate)
            + 0.1 * _channel_similarity(target, candidate)
        )
        reranked.append((candidate, score))
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked
