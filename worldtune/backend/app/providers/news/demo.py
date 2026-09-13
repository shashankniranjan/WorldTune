"""Deterministic demo news -- the DEMO_MODE=true path.

~26 headlines written to exercise the persona's actual interest surface:
AI/semis, crypto, data platforms, macro, and the career-adjacent hiring
signals. Each carries a relative age in hours so news volume and sentiment
have a *shape* over the last 30 days and the trend engine sees a real
distribution rather than a spike at t=0.

Entities/tickers/sectors are resolved through the same entity graph the real
adapters use, so the demo path exercises the production code path.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.analytics.sentiment import score_sentiment
from app.entities.graph import get_entity_graph
from app.providers.base import NewsProvider
from app.schemas.canonical import CanonicalNewsEvent

# (hours_ago, headline, domain)
DEMO_HEADLINES: tuple[tuple[int, str, str], ...] = (
    (3,    "Nvidia beats revenue estimates as AI data centre demand surges", "reuters.com"),
    (7,    "Bitcoin rallies past $64,000 as ETF inflows hit a record week", "coindesk.com"),
    (11,   "Databricks expands Unity Catalog with native Apache Iceberg support", "techcrunch.com"),
    (18,   "Ethereum staking withdrawals spike after protocol upgrade", "theblock.co"),
    (26,   "Microsoft expands Fabric with agent orchestration for data teams", "zdnet.com"),
    (33,   "AI infrastructure spending forecast raised on inference growth", "bloomberg.com"),
    (41,   "AMD misses on data centre guidance, shares drop in late trading", "cnbc.com"),
    (52,   "Snowflake downgraded on slowing consumption growth", "barrons.com"),
    (60,   "Confluent reports strong Kafka cloud adoption among enterprises", "venturebeat.com"),
    (74,   "Federal Reserve signals a possible rate cut, risk assets rally", "wsj.com"),
    (88,   "Google Cloud launches BigQuery vector search for RAG workloads", "theregister.com"),
    (97,   "Bitcoin miners face margin pressure after difficulty record", "coindesk.com"),
    (112,  "OpenAI releases agent framework aimed at production workloads", "theverge.com"),
    (130,  "Apache Iceberg adoption accelerates across lakehouse vendors", "infoq.com"),
    (152,  "Layoffs hit legacy ETL vendors as budgets shift to AI platforms", "businessinsider.com"),
    (168,  "India tech hiring rebounds, data and AI roles lead the gains", "economictimes.com"),
    (190,  "NVIDIA announces next-generation inference accelerator", "tomshardware.com"),
    (214,  "Ethereum layer-2 activity hits all-time high", "decrypt.co"),
    (240,  "Anthropic expands enterprise agent tooling", "axios.com"),
    (270,  "dbt Labs ships semantic layer improvements for analytics engineers", "infoworld.com"),
    (310,  "Crypto selloff as liquidity tightens ahead of CPI print", "ft.com"),
    (350,  "Flink and streaming workloads grow as batch pipelines migrate", "thenewstack.io"),
    (420,  "Microsoft Azure wins large AI infrastructure contract", "reuters.com"),
    (500,  "Vector database funding round signals continued RAG investment", "techcrunch.com"),
    (600,  "Bengaluru data platform teams expand as global firms scale GCC hubs", "livemint.com"),
    (700,  "Kubernetes adoption plateaus while platform engineering roles grow", "thenewstack.io"),
)


class DemoNewsProvider(NewsProvider):
    name = "demo:news"
    is_live = False

    def __init__(self, as_of: datetime | None = None):
        self._as_of = as_of or datetime.now(timezone.utc)

    def is_available(self) -> bool:
        return True

    def fetch_news(self, *, query: str = "", since: datetime | None = None,
                   limit: int = 50) -> list[CanonicalNewsEvent]:
        graph = get_entity_graph()
        events: list[CanonicalNewsEvent] = []
        needle = (query or "").strip().lower()
        for hours_ago, title, domain in DEMO_HEADLINES:
            if needle and needle not in title.lower():
                continue
            published = self._as_of - timedelta(hours=hours_ago)
            if since is not None and published < since:
                continue
            keys = graph.resolve_text(title)
            events.append(
                CanonicalNewsEvent(
                    title=title,
                    summary="",
                    url=f"https://{domain}/worldtune-demo/{abs(hash(title)) % 10**8}",
                    published_at=published,
                    source="demo:news",
                    domain=domain,
                    language="en",
                    sentiment=score_sentiment(title),
                    entities=[graph.label(k) for k in keys],
                    tickers=graph.tickers_for(keys),
                    sectors=graph.sectors_for(keys),
                )
            )
        return events[:limit]
