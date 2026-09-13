from datetime import datetime, timedelta, timezone

from worldpulse.events.classifier import RuleBasedEventClassifier
from worldpulse.events.deduplication import cluster_events
from worldpulse.ingestion.worldmonitor import RawNewsItem

classifier = RuleBasedEventClassifier()


def make_item(item_id, published_at, headline, countries, entities, channels, category, severity):
    return RawNewsItem(
        id=item_id, published_at=published_at, headline=headline, body=headline,
        countries=countries, entities=entities, channels=channels,
        category_hint=category, severity_hint=severity, source_name="test",
        corroboration_count=1,
    )


def test_near_duplicate_articles_cluster_together():
    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    item_a = make_item("a", t0, "Russia masses troops near Ukraine border",
                        ["Russia", "Ukraine"], ["Naval Fleet"], ["shipping_lanes", "regional_security"],
                        "military", 0.7)
    item_b = make_item("b", t0 + timedelta(hours=1), "Russia masses troops near Ukraine border",
                        ["Russia", "Ukraine"], ["Naval Fleet"], ["shipping_lanes", "regional_security"],
                        "military", 0.72)

    events = [classifier.classify(item_a), classifier.classify(item_b)]
    clustered = cluster_events(events, window_hours=6, similarity_threshold=0.55)

    assert clustered[0].event_cluster_id == clustered[1].event_cluster_id
    assert clustered[0].event_cluster_id is not None


def test_distinct_events_do_not_cluster():
    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    item_a = make_item("a", t0, "Russia masses troops near Ukraine border",
                        ["Russia", "Ukraine"], ["Naval Fleet"], ["shipping_lanes", "regional_security"],
                        "military", 0.7)
    item_b = make_item("b", t0 + timedelta(hours=2), "Major pipeline explosion disrupts Saudi Arabia energy exports",
                        ["Saudi Arabia"], ["Pipeline Operator"], ["energy_supply", "shipping_lanes"],
                        "energy", 0.6)

    events = [classifier.classify(item_a), classifier.classify(item_b)]
    clustered = cluster_events(events, window_hours=6, similarity_threshold=0.55)

    assert clustered[0].event_cluster_id != clustered[1].event_cluster_id


def test_events_outside_time_window_do_not_cluster_even_if_similar():
    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    item_a = make_item("a", t0, "Russia masses troops near Ukraine border",
                        ["Russia", "Ukraine"], ["Naval Fleet"], ["shipping_lanes", "regional_security"],
                        "military", 0.7)
    item_b = make_item("b", t0 + timedelta(hours=20), "Russia masses troops near Ukraine border",
                        ["Russia", "Ukraine"], ["Naval Fleet"], ["shipping_lanes", "regional_security"],
                        "military", 0.7)

    events = [classifier.classify(item_a), classifier.classify(item_b)]
    clustered = cluster_events(events, window_hours=6, similarity_threshold=0.55)

    assert clustered[0].event_cluster_id != clustered[1].event_cluster_id
