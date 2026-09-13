"""Feature derivation for the impact_candidate_score gate.

Builds an `ImpactScoreInputs` from a WorldEvent plus retrieval context
(novelty = 1 - similarity to the most similar recent event already seen).
"""
from __future__ import annotations

from worldpulse.events import impact_channels
from worldpulse.events.classifier import RuleBasedEventClassifier
from worldpulse.events.schemas import ImpactScoreInputs, WorldEvent
from worldpulse.similarity.embeddings import cosine_similarity, embed_event

_classifier_priors = RuleBasedEventClassifier()


def compute_novelty(event: WorldEvent, recent_events: list[WorldEvent]) -> float:
    """1 - max cosine similarity to any recent event (excluding itself)."""
    if event.embedding is None:
        event.embedding = embed_event(event)
    max_sim = 0.0
    for other in recent_events:
        if other.id == event.id:
            continue
        other_emb = other.embedding if other.embedding is not None else embed_event(other)
        sim = cosine_similarity(event.embedding, other_emb)
        max_sim = max(max_sim, sim)
    return max(0.0, 1.0 - max_sim)


def build_impact_inputs(event: WorldEvent, recent_events: list[WorldEvent]) -> ImpactScoreInputs:
    corroboration_norm = min(1.0, event.corroboration_count / 5.0)
    novelty = compute_novelty(event, recent_events)
    # Prefer the *rule-level* market relevance from
    # config/impact_channels.yaml (e.g. "earthquake + Taiwan -> 0.85")
    # over the coarse per-domain prior (natural_disaster -> 0.55), falling
    # back to the domain prior when no specific rule matched.
    mapping = impact_channels.get_table().resolve(event)
    market_relevance = mapping.market_relevance or _classifier_priors.market_relevance_prior(
        event.event_type
    )
    geo_relevance = _classifier_priors.geo_relevance(event.countries)
    return ImpactScoreInputs(
        severity=event.severity,
        corroboration=corroboration_norm,
        novelty=novelty,
        historical_market_relevance=market_relevance,
        geographic_relevance=geo_relevance,
        source_confidence=event.source_confidence,
    )
