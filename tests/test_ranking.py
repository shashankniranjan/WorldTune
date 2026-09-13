from datetime import datetime, timezone

from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.similarity.embeddings import embed_event
from worldpulse.similarity.ranking import rerank
from worldpulse.similarity.retrieval import retrieve_analogues


def make_event(event_id, event_type, subtype, countries, entities, channels, severity):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return WorldEvent(
        id=event_id, source_id=event_id, occurred_at=now, ingested_at=now,
        event_type=event_type, event_subtype=subtype, countries=countries,
        entities=entities, affected_channels=channels, potential_assets=[],
        severity=severity, headline=f"headline {event_id}",
    )


def test_reranking_orders_closer_analogues_higher():
    target = make_event("t", EventDomain.MILITARY, "missile_strike", ["Russia", "Ukraine"],
                         ["Naval Fleet"], ["shipping_lanes", "regional_security"], 0.7)
    close_match = make_event("close", EventDomain.MILITARY, "missile_strike", ["Russia", "Ukraine"],
                              ["Naval Fleet"], ["shipping_lanes", "regional_security"], 0.68)
    far_match = make_event("far", EventDomain.MILITARY, "naval_incident", ["Taiwan", "China"],
                            ["Disaster Relief Agency"], ["infrastructure"], 0.45)

    target.embedding = embed_event(target)
    close_match.embedding = embed_event(close_match)
    far_match.embedding = embed_event(far_match)

    scored = retrieve_analogues(target, [close_match, far_match], top_k=10)
    reranked = rerank(target, scored)

    ranked_ids = [c.id for c, _ in reranked]
    assert ranked_ids[0] == "close"
    assert reranked[0][1] > reranked[-1][1]


def test_rerank_is_deterministic():
    target = make_event("t", EventDomain.CONFLICT, "ceasefire_breakdown", ["Israel", "Iran"],
                         ["Government"], ["diplomatic_relations"], 0.5)
    a = make_event("a", EventDomain.CONFLICT, "ceasefire_breakdown", ["Israel", "Iran"],
                    ["Government"], ["diplomatic_relations"], 0.5)
    b = make_event("b", EventDomain.CONFLICT, "ceasefire_breakdown", ["Israel", "Iran"],
                    ["Government"], ["diplomatic_relations"], 0.5)

    scored = retrieve_analogues(target, [a, b], top_k=10)
    reranked_1 = rerank(target, scored)
    reranked_2 = rerank(target, scored)
    assert [c.id for c, _ in reranked_1] == [c.id for c, _ in reranked_2]
