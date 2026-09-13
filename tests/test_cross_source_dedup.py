"""Cross-source dedup: one real event reported by three providers.

The 2024 Hualien (Taiwan) earthquake would arrive at WorldPulse three
times: as a USGS ComCat seismic record, as a GDELT news article, and as an
EONET natural-event entry. They agree on time and place but share almost
no vocabulary, so embedding similarity alone cannot merge them. These
tests assert the geo/time/type rule does, and that the merge produces one
`EventEvidence` row per contributing source rather than dropping two of
the three records.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests import provider_fixtures as fx
from worldpulse.database.repository import (
    add_evidence,
    get_evidence_for_cluster,
    get_evidence_for_event,
    save_events,
)
from worldpulse.events.deduplication import (
    build_cluster_evidence,
    cluster_events,
    is_cross_source_match,
)
from worldpulse.ingestion.providers.eonet import EONETProvider
from worldpulse.ingestion.providers.gdelt import GDELTProvider
from worldpulse.ingestion.providers.usgs import USGSProvider

QUAKE_AT = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)


def _three_records():
    """The same Hualien earthquake, as each real provider would emit it."""
    client = fx.make_client()
    usgs = next(
        e for e in USGSProvider(client=client).fetch_events(fx.WINDOW_START, fx.WINDOW_END)
        if e.provider_event_id == "us7000abcd"
    )
    gdelt = next(
        e for e in GDELTProvider(client=client).fetch_events(fx.WINDOW_START, fx.WINDOW_END)
        if "Taiwan" in e.headline
    )
    eonet = next(
        e for e in EONETProvider(client=client).fetch_events(fx.WINDOW_START, fx.WINDOW_END)
        if e.provider_event_id == "EONET_6789"
    )
    return usgs, gdelt, eonet


def test_three_providers_describing_one_quake_share_a_cluster_id():
    usgs, gdelt, eonet = _three_records()
    assert {usgs.provider, gdelt.provider, eonet.provider} == {"usgs", "gdelt", "eonet"}

    clustered = cluster_events([usgs, gdelt, eonet])

    cluster_ids = {e.event_cluster_id for e in clustered}
    assert len(cluster_ids) == 1, (
        "USGS + GDELT + EONET records for the same quake must land in one cluster, got "
        f"{[(e.provider, e.event_cluster_id) for e in clustered]}"
    )
    assert all(e.event_cluster_id is not None for e in clustered)


def test_merge_produces_one_evidence_row_per_source(db_session):
    usgs, gdelt, eonet = _three_records()
    clustered = cluster_events([usgs, gdelt, eonet])
    cluster_id = clustered[0].event_cluster_id

    save_events(db_session, clustered)
    inserted = add_evidence(db_session, build_cluster_evidence(clustered))
    assert inserted == 3

    evidence = get_evidence_for_cluster(db_session, cluster_id)
    assert len(evidence) == 3, "no contributing source may be dropped on merge"
    assert {e.provider for e in evidence} == {"usgs", "gdelt", "eonet"}
    # Each row keeps a way back to its own upstream record.
    assert all(e.provider_event_id for e in evidence)
    assert all(e.observed_at.tzinfo is not None for e in evidence)

    # Per-event lookup also works, and adding the same evidence twice is a
    # no-op (ingestion is re-runnable).
    assert len(get_evidence_for_event(db_session, usgs.id)) == 1
    assert add_evidence(db_session, build_cluster_evidence(clustered)) == 0


def test_point_located_quakes_far_apart_do_not_merge():
    """Same minute, same type, 8000 km apart -> two different events."""
    usgs, gdelt, eonet = _three_records()
    distant = eonet.model_copy(deep=True)
    distant.provider = "gdacs"
    distant.provider_event_id = "EQ999"
    distant.source_id = "gdacs:EQ999"
    distant.id = "distant-quake"
    distant.latitude = 38.0
    distant.longitude = -122.0
    distant.locations = ["California"]
    distant.countries = ["USA"]
    distant.headline = "Earthquake off the coast of northern California"

    assert not is_cross_source_match(usgs, distant)
    clustered = cluster_events([usgs, distant])
    assert clustered[0].event_cluster_id != clustered[1].event_cluster_id


def test_point_located_quakes_outside_tight_window_do_not_merge():
    """Co-located but 5 hours apart: two separate quakes, not one.

    Point-located disasters use the tighter `cross_source_geo_window_hours`
    (2h) window precisely so an aftershock sequence is not collapsed into
    the mainshock.
    """
    usgs, _gdelt, eonet = _three_records()
    aftershock = eonet.model_copy(deep=True)
    aftershock.provider = "gdacs"
    aftershock.provider_event_id = "EQ1000"
    aftershock.source_id = "gdacs:EQ1000"
    aftershock.id = "aftershock"
    aftershock.occurred_at = usgs.occurred_at + timedelta(hours=5)

    assert not is_cross_source_match(usgs, aftershock)


def test_incompatible_domains_never_merge():
    """A rate decision and an earthquake at the same time/place stay apart."""
    usgs, gdelt, _eonet = _three_records()
    policy = gdelt.model_copy(deep=True)
    policy.id = "policy-event"
    policy.provider = "gdelt"
    policy.provider_event_id = "https://example.test/rate-decision"
    policy.source_id = "gdelt:rate"
    from worldpulse.events.schemas import EventDomain

    policy.event_type = EventDomain.ECONOMIC.value
    policy.event_domain = EventDomain.ECONOMIC.value
    policy.event_subtype = "rate_decision"

    assert not is_cross_source_match(usgs, policy)


def test_same_provider_pairs_use_the_embedding_path_not_the_geo_rule():
    """The cross-source rule must not fire within a single feed.

    Two USGS records are two distinct quakes by construction; only the
    embedding/entity path may merge same-provider records.
    """
    usgs, _gdelt, _eonet = _three_records()
    twin = usgs.model_copy(deep=True)
    twin.id = "usgs-twin"
    twin.provider_event_id = "us7000abce"
    twin.source_id = "usgs:us7000abce"

    assert not is_cross_source_match(usgs, twin)


def test_existing_same_provider_news_dedup_still_works():
    """Regression guard: the pre-existing embedding path is untouched."""
    from worldpulse.events.classifier import RuleBasedEventClassifier
    from worldpulse.ingestion.worldmonitor import RawNewsItem

    classifier = RuleBasedEventClassifier()
    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    def item(item_id, when):
        return RawNewsItem(
            id=item_id, published_at=when,
            headline="Russia masses troops near Ukraine border",
            body="", countries=["Russia", "Ukraine"], entities=["Border Forces"],
            channels=["regional_security"], category_hint="military",
            severity_hint=0.7, source_name="test", corroboration_count=1,
        )

    events = [classifier.classify(item("a", t0)),
              classifier.classify(item("b", t0 + timedelta(hours=1)))]
    clustered = cluster_events(events, window_hours=6, similarity_threshold=0.55)
    assert clustered[0].event_cluster_id == clustered[1].event_cluster_id
