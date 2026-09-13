"""Deduplication / clustering of WorldEvent records.

Two complementary merge criteria run over the same union-find, in order:

1. **Cross-source geo/time/type merge** (first pass, added by the
   multi-provider refactor). Two records from *different* providers -- a
   USGS earthquake, a GDELT article about that earthquake, an EONET entry
   for it -- describe the same real-world event when they agree on
   time, place and kind. Embedding similarity cannot see this: USGS's
   `"M 7.4 - 18 km SSE of Hualien City, Taiwan"` and a newspaper's
   `"Powerful quake rocks eastern Taiwan"` share almost no tokens. So this
   pass matches on:
     * **time proximity** -- within `cross_source_window_hours` (default
       6h), tightened to `cross_source_geo_window_hours` (default 2h) when
       both records are point-located disasters, where the physical event
       is instantaneous and a wider window would over-merge;
     * **geographic distance** -- haversine within
       `cross_source_geo_radius_km` (default 150 km) when both have
       lat/lon; when only one does, geography is treated as unknown rather
       than as a mismatch and the other criteria must carry the match;
     * **event type/domain compatibility** -- same domain, plus compatible
       `event_subtype` (see `_COMPATIBLE_SUBTYPES`);
     * **entity/keyword overlap** -- a shared country/entity, or a shared
       significant headline/location token.

2. **Same-provider embedding-similarity merge** (the pre-existing path,
   unchanged in behaviour). Events inside `window_hours` whose embedding
   cosine similarity exceeds `similarity_threshold` AND which share at
   least one entity or country are the same story reported twice. This is
   what collapses near-duplicate news articles.

When records merge, `build_cluster_evidence` produces one `EventEvidence`
row per contributing source, so the non-winning records are preserved as
provenance instead of being dropped.
"""
from __future__ import annotations

import re
import uuid
from datetime import timedelta

from worldpulse.config import settings
from worldpulse.events.schemas import EventEvidence, WorldEvent
from worldpulse.ingestion.providers.base import haversine_km
from worldpulse.similarity.embeddings import cosine_similarity, embed_event

#: Subtypes that different providers legitimately use for the same physical
#: event. Each set is mutually compatible.
_COMPATIBLE_SUBTYPES: list[set[str]] = [
    {"earthquake", "tsunami", "general"},
    {"storm", "tropical_cyclone", "flooding", "general"},
    {"wildfire", "general"},
    {"volcanic_eruption", "general"},
    {"landslide", "flooding", "general"},
    {"missile_strike", "armed_clash", "naval_incident", "troop_movement", "general"},
    {"pipeline_disruption", "refinery_disruption", "shipping_disruption", "general"},
    {"rate_decision", "inflation_shock", "sanctions", "general"},
]

#: Subtypes describing an instantaneous, point-located physical event,
#: where the tighter time window + distance rule applies.
_POINT_LOCATED_SUBTYPES = frozenset({
    "earthquake", "volcanic_eruption", "tsunami", "landslide", "wildfire",
    "missile_strike", "naval_incident", "armed_clash",
})

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "from",
    "by", "with", "as", "is", "are", "was", "were", "be", "been", "after",
    "near", "amid", "over", "into", "new", "says", "said", "km", "reports",
    "reported", "report", "m", "magnitude", "gdacs", "alert",
})


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-z0-9]+", (text or "").lower())
        if len(token) > 3 and token not in _STOPWORDS
    }


def _entity_location_overlap(a: WorldEvent, b: WorldEvent) -> bool:
    a_tokens = set(a.entities) | set(a.countries)
    b_tokens = set(b.entities) | set(b.countries)
    return len(a_tokens & b_tokens) > 0


def _subtypes_compatible(a: WorldEvent, b: WorldEvent) -> bool:
    sa, sb = (a.event_subtype or "general"), (b.event_subtype or "general")
    if sa == sb:
        return True
    return any(sa in group and sb in group for group in _COMPATIBLE_SUBTYPES)


def _domains_equal(a: WorldEvent, b: WorldEvent) -> bool:
    def domain(event: WorldEvent) -> str:
        value = event.event_type
        return value.value if hasattr(value, "value") else str(value)

    return domain(a) == domain(b)


def _keyword_overlap(a: WorldEvent, b: WorldEvent) -> bool:
    """Shared country/entity, or a shared significant headline/place token."""
    if _entity_location_overlap(a, b):
        return True
    a_text = " ".join([a.headline, " ".join(a.locations), " ".join(a.countries)])
    b_text = " ".join([b.headline, " ".join(b.locations), " ".join(b.countries)])
    return len(_tokens(a_text) & _tokens(b_text)) > 0


def is_cross_source_match(
    a: WorldEvent,
    b: WorldEvent,
    *,
    window_hours: float | None = None,
    geo_window_hours: float | None = None,
    geo_radius_km: float | None = None,
) -> bool:
    """Whether two records from DIFFERENT providers describe one real event.

    Returns False for same-provider pairs -- those go through the
    embedding-similarity path instead, which is better at catching
    near-duplicate wording from one feed.
    """
    if not a.provider or not b.provider or a.provider == b.provider:
        return False
    if not _domains_equal(a, b) or not _subtypes_compatible(a, b):
        return False

    window_hours = settings.cross_source_window_hours if window_hours is None else window_hours
    geo_window_hours = (
        settings.cross_source_geo_window_hours if geo_window_hours is None else geo_window_hours
    )
    geo_radius_km = (
        settings.cross_source_geo_radius_km if geo_radius_km is None else geo_radius_km
    )

    both_point_located = (
        a.has_point_location() and b.has_point_location()
        and a.event_subtype in _POINT_LOCATED_SUBTYPES
        and b.event_subtype in _POINT_LOCATED_SUBTYPES
    )
    effective_window = geo_window_hours if both_point_located else window_hours
    if abs(a.occurred_at - b.occurred_at) > timedelta(hours=effective_window):
        return False

    if a.has_point_location() and b.has_point_location():
        distance = haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
        if distance > geo_radius_km:
            return False
        # Co-located in space and time, same domain and compatible type:
        # that is already a strong match; a shared token is a bonus, not a
        # requirement (a wire headline may name no country USGS knows).
        return True

    # No usable geometry on at least one side: geography is *unknown*, not
    # mismatched, so the textual/entity criterion has to carry the match.
    return _keyword_overlap(a, b)


def cluster_events(
    events: list[WorldEvent],
    window_hours: float = 6.0,
    similarity_threshold: float = 0.55,
    cross_source: bool = True,
) -> list[WorldEvent]:
    """Assign `event_cluster_id` in-place (on the given objects) and return them.

    Union-find over pairs satisfying either merge criterion. Deterministic
    given the input order.
    """
    n = len(events)
    events = list(events)
    for e in events:
        if e.embedding is None:
            e.embedding = embed_event(e)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    window = timedelta(hours=window_hours)
    # The cross-source rule may use a wider window than `window_hours`, so
    # the cheap time pre-filter has to use the larger of the two.
    max_window = timedelta(
        hours=max(window_hours, settings.cross_source_window_hours if cross_source else 0.0)
    )

    for i in range(n):
        for j in range(i + 1, n):
            a, b = events[i], events[j]
            if abs(a.occurred_at - b.occurred_at) > max_window:
                continue

            # Pass 1: cross-source geo/time/type merge.
            if cross_source and is_cross_source_match(a, b):
                union(i, j)
                continue

            # Pass 2: same-feed embedding similarity (pre-existing logic).
            if abs(a.occurred_at - b.occurred_at) > window:
                continue
            sim = cosine_similarity(a.embedding, b.embedding)
            if sim > similarity_threshold and _entity_location_overlap(a, b):
                union(i, j)

    # Deterministic cluster IDs: derive from the sorted source_ids in the
    # cluster so re-running clustering on the same input is stable.
    root_to_id: dict[int, str] = {}
    for i in range(n):
        root = find(i)
        if root not in root_to_id:
            members = [events[k].source_id for k in range(n) if find(k) == root]
            seed = "|".join(sorted(members))
            root_to_id[root] = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
    for i in range(n):
        events[i].event_cluster_id = root_to_id[find(i)]

    return events


def group_by_cluster(events: list[WorldEvent]) -> dict[str, list[WorldEvent]]:
    """Clustered events grouped by `event_cluster_id`."""
    groups: dict[str, list[WorldEvent]] = {}
    for event in events:
        key = event.event_cluster_id or (event.id or event.source_id)
        groups.setdefault(key, []).append(event)
    return groups


def apply_cluster_corroboration(events: list[WorldEvent]) -> list[WorldEvent]:
    """Set `corroboration_count` from the number of distinct providers.

    `corroboration_count` means "how many independent sources reported
    this event", and cross-source clustering is precisely what makes that
    measurable now: a quake seen by USGS, GDELT, EONET and GDACS is
    4-source-corroborated, and the impact-score gate should treat it as
    such. Must be called AFTER `cluster_events`.
    """
    groups = group_by_cluster(events)
    for members in groups.values():
        providers = {m.provider for m in members if m.provider}
        count = max(1, len(providers) or len(members))
        for member in members:
            # Never lower a provider-supplied count (e.g. World Monitor
            # ships its own corroboration figure).
            member.corroboration_count = max(member.corroboration_count, count)
            if count > 1:
                # Independent agreement raises confidence in the record.
                member.source_confidence = min(
                    1.0, member.source_confidence + 0.02 * (count - 1)
                )
    return events


def build_cluster_evidence(events: list[WorldEvent]) -> list[EventEvidence]:
    """One `EventEvidence` per contributing source, for every cluster.

    Each event in a cluster contributes evidence attached to *its own*
    event id -- nothing is dropped on merge, so a cluster's full source
    list is recoverable via
    `repository.get_evidence_for_cluster(cluster_id)`.
    """
    evidence: list[EventEvidence] = []
    for event in events:
        if not event.id:
            continue
        evidence.append(EventEvidence(
            event_id=event.id,
            provider=event.provider or "unknown",
            provider_event_id=event.provider_event_id or event.source_id,
            source_url=event.source_url,
            source_name=event.source_name or event.provider,
            observed_at=event.first_seen_at or event.ingested_at,
            raw_payload=event.raw_payload,
        ))
    return evidence
