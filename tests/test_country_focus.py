"""COUNTRY_FOCUS=IN narrows the free providers to India-related events.

Covers all three filtering mechanisms used across the providers:
  * GDELT: server-side query augmentation (`sourcecountry:IN`)
  * USGS: server-side FDSN bbox params + a client-side bbox safety net
  * EONET/GDACS: pure client-side bbox/country/text filtering (neither API
    supports a country parameter)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from worldpulse.config import settings
from worldpulse.ingestion.providers.country_focus import CountryFocus, get_focus, matches


@pytest.fixture(autouse=True)
def _reset_country_focus():
    original = settings.country_focus
    yield
    settings.country_focus = original


def test_get_focus_unset_returns_none():
    settings.country_focus = None
    assert get_focus() is None


def test_get_focus_unknown_code_returns_none():
    settings.country_focus = "ZZ"
    assert get_focus() is None


def test_get_focus_india():
    settings.country_focus = "in"  # case-insensitive
    focus = get_focus()
    assert focus is not None
    assert focus.iso2 == "IN"
    assert focus.name == "India"


INDIA = CountryFocus(
    iso2="IN", name="India", gdelt_fips="IN",
    bbox=(5.0, 38.0, 66.0, 99.0),
    name_hints=("india", "mumbai", "delhi"),
)


def test_matches_by_bbox_inside():
    # Mumbai
    assert matches(INDIA, lat=19.07, lon=72.87) is True


def test_matches_by_bbox_outside():
    # Tokyo
    assert matches(INDIA, lat=35.68, lon=139.69) is False


def test_matches_by_country_name():
    assert matches(INDIA, countries=["India"]) is True
    assert matches(INDIA, countries=["Japan"]) is False


def test_matches_by_text_hint():
    assert matches(INDIA, text="Earthquake reported near Mumbai coast") is True
    assert matches(INDIA, text="Earthquake reported near Tokyo") is False


def test_gdelt_appends_sourcecountry_when_focused():
    from worldpulse.ingestion.providers.gdelt import GDELTProvider

    settings.country_focus = "IN"
    provider = GDELTProvider()
    captured_queries: list[str] = []

    def fake_query_articles(query, start_time, end_time):
        captured_queries.append(query)
        return []

    with patch.object(provider, "_query_articles", side_effect=fake_query_articles):
        provider._fetch(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    assert captured_queries, "expected at least one domain query"
    assert all("sourcecountry:IN" in q for q in captured_queries)


def test_gdelt_no_country_filter_by_default():
    from worldpulse.ingestion.providers.gdelt import GDELTProvider

    settings.country_focus = None
    provider = GDELTProvider()
    captured_queries: list[str] = []

    def fake_query_articles(query, start_time, end_time):
        captured_queries.append(query)
        return []

    with patch.object(provider, "_query_articles", side_effect=fake_query_articles):
        provider._fetch(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    assert captured_queries and all("sourcecountry:" not in q for q in captured_queries)


def test_usgs_fdsn_query_gets_bbox_when_focused():
    from worldpulse.ingestion.providers import usgs as usgs_module

    settings.country_focus = "IN"
    provider = usgs_module.USGSProvider()
    captured_params: list[dict] = []

    def fake_http_get_json(url, params=None, client=None):
        captured_params.append(params or {})
        return {"features": []}

    with patch.object(usgs_module.http_utils, "http_get_json", side_effect=fake_http_get_json):
        provider._fetch_fdsn_range(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    assert captured_params
    p = captured_params[0]
    assert p["minlatitude"] == pytest.approx(5.0)
    assert p["maxlatitude"] == pytest.approx(38.0)
    assert p["minlongitude"] == pytest.approx(66.0)
    assert p["maxlongitude"] == pytest.approx(99.0)


def test_usgs_client_side_bbox_filters_features():
    from worldpulse.ingestion.providers import usgs as usgs_module

    settings.country_focus = "IN"
    provider = usgs_module.USGSProvider(min_magnitude=0.0)

    india_feature = {
        "id": "in1", "type": "Feature",
        "properties": {"mag": 5.0, "time": 1704067200000, "place": "India"},
        "geometry": {"type": "Point", "coordinates": [77.2, 28.6, 10.0]},  # Delhi
    }
    japan_feature = {
        "id": "jp1", "type": "Feature",
        "properties": {"mag": 6.0, "time": 1704067200000, "place": "Japan"},
        "geometry": {"type": "Point", "coordinates": [139.69, 35.68, 10.0]},  # Tokyo
    }

    with patch.object(provider, "_fetch_fdsn_range", return_value=[india_feature, japan_feature]):
        events = provider._fetch(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    ids = {e.provider_event_id for e in events}
    assert ids == {"in1"}
