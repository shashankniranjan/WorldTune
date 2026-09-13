"""Provider normalization -- fixture-driven, HTTP fully mocked.

No test here touches the network. Each real adapter's `parse` is exercised
against a hand-built payload shaped like the genuine API response (including
its quirks), which is what makes these tests meaningful offline: they verify
the parsing contract, which is the part of a provider that actually breaks.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.providers.jobs.adzuna import AdzunaProvider
from app.providers.jobs.classify import classify_role_family, classify_seniority, is_remote
from app.providers.jobs.demo import DemoJobsProvider
from app.providers.jobs.remoteok import RemoteOKProvider, strip_html
from app.providers.market.coingecko import CoinGeckoProvider
from app.providers.market.demo import DemoMarketDataProvider
from app.providers.market.stooq import StooqProvider
from app.providers.news.demo import DemoNewsProvider
from app.providers.news.gdelt import GDELTNewsProvider
from app.providers.news.googlenews import GoogleNewsRSSProvider
from app.providers.technology.demo import DemoTechnologyProvider
from app.providers.technology.github import GitHubTechnologyProvider
from app.providers.technology.hackernews import HackerNewsTechnologyProvider
from app.schemas.canonical import (
    CanonicalJob,
    CanonicalMarketPrice,
    CanonicalNewsEvent,
    CanonicalTechEvent,
)

AS_OF = datetime(2025, 9, 13, 12, 0, tzinfo=timezone.utc)


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# --- CoinGecko ---------------------------------------------------------------

class TestCoinGecko:
    OHLC = [
        [1757116800000, 60000.0, 61500.0, 59800.0, 61200.0],
        [1757203200000, 61200.0, 62000.0, 60900.0, 61800.0],
    ]
    CHART = {"total_volumes": [[1757116800000, 2.5e10], [1757203200000, 2.7e10]]}

    def test_merges_ohlc_with_volume_by_date(self):
        bars = CoinGeckoProvider.parse("BTC", self.OHLC, self.CHART)
        assert len(bars) == 2
        assert all(isinstance(b, CanonicalMarketPrice) for b in bars)
        assert bars[0].close == 61200.0
        assert bars[0].volume == 2.5e10
        assert bars[0].asset_class == "crypto"
        assert bars[0].timestamp.tzinfo is not None

    def test_bar_without_matching_volume_is_kept_with_zero(self):
        """Losing a price bar to a missing volume would corrupt the return series."""
        bars = CoinGeckoProvider.parse("BTC", self.OHLC, {"total_volumes": []})
        assert len(bars) == 2
        assert bars[0].volume == 0.0

    def test_malformed_rows_are_skipped(self):
        bars = CoinGeckoProvider.parse("BTC", [[1757116800000, 1.0], "junk", None], {})
        assert bars == []

    def test_fetch_uses_http_and_returns_canonical(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if "/ohlc" in request.url.path:
                return httpx.Response(200, json=self.OHLC)
            return httpx.Response(200, json=self.CHART)

        provider = CoinGeckoProvider(client=mock_client(handler))
        bars = provider.fetch_prices(["BTC"], days=2)
        assert len(bars) == 2 and bars[0].source == "coingecko"

    def test_unknown_symbol_is_skipped(self):
        provider = CoinGeckoProvider(client=mock_client(
            lambda r: httpx.Response(200, json=[])))
        assert provider.fetch_prices(["NOTACOIN"]) == []


# --- Stooq -------------------------------------------------------------------

class TestStooq:
    CSV = (
        "Date,Open,High,Low,Close,Volume\n"
        "2025-09-10,118.00,120.50,117.20,119.80,310000000\n"
        "2025-09-11,119.80,121.00,119.00,120.40,295000000\n"
    )

    def test_parses_daily_csv(self):
        bars = StooqProvider.parse("NVDA", self.CSV)
        assert len(bars) == 2
        assert bars[0].close == 119.80
        assert bars[0].asset_class == "equity"
        assert bars[0].timestamp == datetime(2025, 9, 10, tzinfo=timezone.utc)

    def test_no_data_body_returns_empty(self):
        """Stooq returns the literal 'No data' with HTTP 200 for a bad symbol."""
        assert StooqProvider.parse("ZZZZ", "No data") == []

    def test_na_volume_becomes_zero(self):
        csv = "Date,Open,High,Low,Close,Volume\n2025-09-10,1,2,0.5,1.5,N/A\n"
        assert StooqProvider.parse("X", csv)[0].volume == 0.0

    def test_row_without_close_is_dropped(self):
        csv = "Date,Open,High,Low,Close,Volume\n2025-09-10,1,2,0.5,,100\n"
        assert StooqProvider.parse("X", csv) == []

    def test_empty_body_returns_empty(self):
        assert StooqProvider.parse("X", "") == []


# --- GDELT -------------------------------------------------------------------

class TestGDELT:
    PAYLOAD = {"articles": [
        {"title": "Nvidia beats revenue estimates on AI demand",
         "url": "https://example.com/a", "seendate": "20250913T104500Z",
         "domain": "example.com", "language": "English"},
        {"title": "", "seendate": "20250913T104500Z"},          # no title -> skipped
        {"title": "No date here"},                               # no date -> skipped
    ]}

    def test_parses_and_resolves_entities(self):
        events = GDELTNewsProvider.parse(self.PAYLOAD)
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CanonicalNewsEvent)
        assert event.published_at == datetime(2025, 9, 13, 10, 45, tzinfo=timezone.utc)
        assert "NVDA" in event.tickers
        assert event.sentiment > 0     # "beats" is a positive lexicon term

    def test_empty_payload(self):
        assert GDELTNewsProvider.parse({}) == []

    def test_fetch_with_mocked_transport(self):
        provider = GDELTNewsProvider(
            client=mock_client(lambda r: httpx.Response(200, json=self.PAYLOAD)),
            queries=("ai",),
        )
        assert len(provider.fetch_news(limit=10)) == 1


# --- Google News RSS ---------------------------------------------------------

class TestGoogleNewsRSS:
    RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>Bitcoin rallies past $64,000 - CoinDesk</title>
    <link>https://news.google.com/x</link>
    <pubDate>Sat, 13 Sep 2025 08:30:00 GMT</pubDate>
    <source url="https://coindesk.com">CoinDesk</source></item>
    </channel></rss>"""

    def test_splits_publisher_suffix_from_headline(self):
        events = GoogleNewsRSSProvider.parse(self.RSS)
        assert len(events) == 1
        assert events[0].title == "Bitcoin rallies past $64,000"
        assert events[0].summary == "CoinDesk"
        assert events[0].domain == "coindesk.com"
        assert "BTC" in events[0].tickers

    def test_malformed_xml_returns_empty_not_raise(self):
        assert GoogleNewsRSSProvider.parse("<rss><broken>") == []


# --- RemoteOK ----------------------------------------------------------------

class TestRemoteOK:
    PAYLOAD = [
        {"legal": "See remoteok.com/api for terms"},      # must be skipped
        {"id": 123, "position": "Senior Data Engineer", "company": "Acme",
         "description": "<p>Work with <b>Spark</b> and Kafka</p>",
         "location": "Worldwide", "date": "2025-09-10T08:00:00+00:00",
         "url": "https://remoteok.com/l/123", "tags": ["python", "spark"],
         "salary_min": 120000, "salary_max": 0},
    ]

    def test_skips_leading_legal_element(self):
        jobs = RemoteOKProvider.parse(self.PAYLOAD)
        assert len(jobs) == 1
        assert isinstance(jobs[0], CanonicalJob)

    def test_strips_html_and_appends_tags(self):
        job = RemoteOKProvider.parse(self.PAYLOAD)[0]
        assert "<p>" not in job.description
        assert "Spark" in job.description
        assert "Tags: python, spark" in job.description

    def test_zero_salary_becomes_none(self):
        """RemoteOK uses 0, not null, for an unknown salary."""
        job = RemoteOKProvider.parse(self.PAYLOAD)[0]
        assert job.salary_min == 120000
        assert job.salary_max is None

    def test_every_posting_is_remote(self):
        assert RemoteOKProvider.parse(self.PAYLOAD)[0].remote is True

    def test_strip_html_unescapes_entities(self):
        assert strip_html("<i>R&amp;D</i> team") == "R&D team"


# --- Adzuna ------------------------------------------------------------------

class TestAdzuna:
    PAYLOAD = {"results": [{
        "id": "9001", "title": "Staff Data Platform Engineer",
        "company": {"display_name": "Acme India"},
        "description": "Spark, Airflow and dbt at scale...",
        "location": {"display_name": "Bengaluru, Karnataka",
                     "area": ["India", "Karnataka", "Bengaluru"]},
        "created": "2025-09-11T06:30:00Z",
        "redirect_url": "https://adzuna.in/job/9001",
        "salary_min": 3500000, "salary_max": 5200000,
    }]}

    def test_parses_nested_company_and_location(self):
        jobs = AdzunaProvider.parse(self.PAYLOAD)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.company == "Acme India"
        assert job.location == "Bengaluru, Karnataka"
        assert job.country == "India"        # area is broadest-first
        assert job.salary_currency == "INR"

    def test_unavailable_without_credentials(self, settings):
        assert AdzunaProvider().is_available() is False

    def test_unavailable_provider_returns_empty_rather_than_raising(self, settings):
        assert AdzunaProvider().fetch_jobs() == []

    def test_available_when_credentials_present(self, settings, monkeypatch):
        monkeypatch.setattr(settings, "adzuna_app_id", "id")
        monkeypatch.setattr(settings, "adzuna_app_key", "key")
        assert AdzunaProvider().is_available() is True


# --- GitHub / HN -------------------------------------------------------------

class TestGitHub:
    PAYLOAD = {"items": [{
        "full_name": "apache/iceberg", "description": "Open table format",
        "html_url": "https://github.com/apache/iceberg", "stargazers_count": 6800,
        "pushed_at": "2025-09-12T10:00:00Z", "topics": ["lakehouse"],
    }]}

    def test_uses_repo_name_not_owner_slash_repo(self):
        events = GitHubTechnologyProvider.parse(self.PAYLOAD, category="lakehouse")
        assert events[0].name == "iceberg"
        assert events[0].stars == 6800
        assert isinstance(events[0], CanonicalTechEvent)

    def test_star_velocity_is_zero_from_a_single_snapshot(self):
        """A single search response carries no star history -- this must not fake one."""
        assert GitHubTechnologyProvider.parse(self.PAYLOAD)[0].stars_7d_delta == 0.0

    def test_available_without_a_token(self, settings):
        assert GitHubTechnologyProvider().is_available() is True


class TestHackerNews:
    PAYLOAD = {"hits": [
        {"objectID": "1", "title": "Apache Iceberg at scale", "url": "https://x.com",
         "points": 210, "num_comments": 88, "created_at_i": 1757673600},
        {"objectID": "2", "points": 5},      # a comment: no title -> skipped
    ]}

    def test_skips_entries_without_a_title(self):
        events = HackerNewsTechnologyProvider.parse(self.PAYLOAD, name="iceberg")
        assert len(events) == 1
        assert events[0].points == 210
        assert events[0].mentions == 88
        assert events[0].stars == 0.0


# --- Demo adapters -----------------------------------------------------------

class TestDemoProviders:
    def test_market_is_deterministic(self):
        a = DemoMarketDataProvider(as_of=AS_OF).fetch_prices(["BTC"], days=40)
        b = DemoMarketDataProvider(as_of=AS_OF).fetch_prices(["BTC"], days=40)
        assert [x.close for x in a] == [x.close for x in b]

    def test_market_equities_skip_weekends_crypto_does_not(self):
        crypto = DemoMarketDataProvider(as_of=AS_OF).fetch_prices(["BTC"], days=28)
        equity = DemoMarketDataProvider(as_of=AS_OF).fetch_prices(["NVDA"], days=28)
        assert len(crypto) == 28
        assert len(equity) < len(crypto)
        assert all(b.timestamp.weekday() < 5 for b in equity)

    def test_market_bars_are_internally_consistent(self):
        for bar in DemoMarketDataProvider(as_of=AS_OF).fetch_prices(["ETH"], days=30):
            assert bar.high >= bar.close >= bar.low
            assert bar.high >= bar.open >= bar.low
            assert bar.volume > 0

    def test_jobs_count_and_spread(self):
        jobs = DemoJobsProvider(as_of=AS_OF).fetch_jobs(limit=100)
        assert 30 <= len(jobs) <= 50
        assert len({j.location for j in jobs}) > 3
        assert len({j.title for j in jobs}) > 5
        assert all(isinstance(j, CanonicalJob) for j in jobs)

    def test_jobs_emerging_skills_are_more_common_in_recent_postings(self):
        """The seeded drift is what gives the trend engine a real signal."""
        jobs = DemoJobsProvider(as_of=AS_OF).fetch_jobs(limit=100)
        recent = [j for j in jobs if (AS_OF - j.posted_at).days <= 20]
        older = [j for j in jobs if (AS_OF - j.posted_at).days >= 40]
        recent_rate = sum("Iceberg" in j.description or "LLM" in j.description
                          for j in recent) / max(1, len(recent))
        older_rate = sum("Iceberg" in j.description or "LLM" in j.description
                         for j in older) / max(1, len(older))
        assert recent_rate > older_rate

    def test_news_headlines_are_spread_over_time(self):
        events = DemoNewsProvider(as_of=AS_OF).fetch_news(limit=100)
        assert len(events) >= 20
        ages = {(AS_OF - e.published_at).days for e in events}
        assert len(ages) > 10

    def test_technology_snapshots_form_a_series(self):
        events = DemoTechnologyProvider(as_of=AS_OF).fetch_tech_events(limit=0)
        by_name: dict[str, list] = {}
        for e in events:
            by_name.setdefault(e.name, []).append(e)
        assert len(by_name) >= 20
        assert all(len(v) >= 2 for v in by_name.values())

    def test_demo_providers_report_demo_mode(self):
        for provider in (DemoMarketDataProvider(), DemoNewsProvider(),
                         DemoJobsProvider(), DemoTechnologyProvider()):
            assert provider.is_live is False
            assert provider.status()["mode"] == "demo"
            assert provider.is_available() is True


# --- classification ----------------------------------------------------------

class TestClassification:
    @pytest.mark.parametrize("title,expected", [
        ("Senior Data Engineer", "senior"),
        ("Staff Data Engineer", "staff"),
        ("Senior Staff Engineer", "staff"),       # most-senior rule wins
        ("Principal Engineer", "principal"),
        ("Junior Data Analyst", "junior"),
        ("Data Engineer", "mid"),
    ])
    def test_seniority(self, title, expected):
        assert classify_seniority(title) == expected

    @pytest.mark.parametrize("title,expected", [
        ("Senior Data Engineer", "data-engineering"),
        ("ML Platform Engineer", "ai-ml"),        # discipline beats surface
        ("Site Reliability Engineer", "platform"),
        ("Data Analyst", "analytics"),
    ])
    def test_role_family(self, title, expected):
        assert classify_role_family(title) == expected

    def test_remote_detection(self):
        assert is_remote("Engineer", "Remote - Global") is True
        assert is_remote("Engineer", "Bengaluru, India") is False
        assert is_remote("Engineer", "", ["remote"]) is True
