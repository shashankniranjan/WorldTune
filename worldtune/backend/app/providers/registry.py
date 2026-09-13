"""Provider selection.

One rule decides everything: `DEMO_MODE` (default true) selects the Demo*
adapters exclusively; DEMO_MODE=false selects the real adapters that report
`is_available()`. A real adapter whose credential is missing is filtered out
here rather than failing at call time, and if *every* real adapter for a kind
is unavailable the demo adapter is returned as a floor -- the dashboard is
never empty because someone forgot a key.

`describe_all()` powers GET /api/system/data-sources: it reports every known
adapter, live or demo, selected or not.
"""
from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.providers.base import (
    JobsProvider,
    MarketDataProvider,
    NewsProvider,
    Provider,
    TechnologySignalsProvider,
)
from app.providers.jobs.adzuna import AdzunaProvider
from app.providers.jobs.demo import DemoJobsProvider
from app.providers.jobs.remoteok import RemoteOKProvider
from app.providers.market.coingecko import CoinGeckoProvider
from app.providers.market.demo import DemoMarketDataProvider
from app.providers.market.stooq import StooqProvider
from app.providers.news.demo import DemoNewsProvider
from app.providers.news.gdelt import GDELTNewsProvider
from app.providers.news.googlenews import GoogleNewsRSSProvider
from app.providers.technology.demo import DemoTechnologyProvider
from app.providers.technology.github import GitHubTechnologyProvider
from app.providers.technology.hackernews import HackerNewsTechnologyProvider


def _live_market() -> list[MarketDataProvider]:
    return [CoinGeckoProvider(), StooqProvider()]


def _live_news() -> list[NewsProvider]:
    return [GDELTNewsProvider(), GoogleNewsRSSProvider()]


def _live_jobs() -> list[JobsProvider]:
    return [RemoteOKProvider(), AdzunaProvider()]


def _live_technology() -> list[TechnologySignalsProvider]:
    return [GitHubTechnologyProvider(), HackerNewsTechnologyProvider()]


def _select(live_factory, demo_factory, *, demo_mode: bool | None = None) -> list[Provider]:
    if settings.demo_mode if demo_mode is None else demo_mode:
        return [demo_factory()]
    available = [p for p in live_factory() if p.is_available()]
    return available or [demo_factory()]


def market_providers(as_of: datetime | None = None,
                     demo_mode: bool | None = None) -> list[MarketDataProvider]:
    return _select(_live_market, lambda: DemoMarketDataProvider(as_of=as_of), demo_mode=demo_mode)


def news_providers(as_of: datetime | None = None,
                   demo_mode: bool | None = None) -> list[NewsProvider]:
    return _select(_live_news, lambda: DemoNewsProvider(as_of=as_of), demo_mode=demo_mode)


def jobs_providers(as_of: datetime | None = None,
                   demo_mode: bool | None = None) -> list[JobsProvider]:
    return _select(_live_jobs, lambda: DemoJobsProvider(as_of=as_of), demo_mode=demo_mode)


def technology_providers(as_of: datetime | None = None,
                         demo_mode: bool | None = None) -> list[TechnologySignalsProvider]:
    return _select(_live_technology, lambda: DemoTechnologyProvider(as_of=as_of),
                   demo_mode=demo_mode)


def describe_all() -> dict:
    """Full inventory for GET /api/system/data-sources."""
    selected = {
        "market": [p.name for p in market_providers()],
        "news": [p.name for p in news_providers()],
        "jobs": [p.name for p in jobs_providers()],
        "technology": [p.name for p in technology_providers()],
    }
    known: list[Provider] = [
        *_live_market(), DemoMarketDataProvider(),
        *_live_news(), DemoNewsProvider(),
        *_live_jobs(), DemoJobsProvider(),
        *_live_technology(), DemoTechnologyProvider(),
    ]
    rows = []
    for provider in known:
        row = provider.status()
        row["selected"] = provider.name in selected.get(row["kind"], [])
        rows.append(row)
    return {
        "demo_mode": settings.demo_mode,
        "selected": selected,
        "providers": rows,
        "note": (
            "DEMO_MODE=true (the default) uses deterministic seeded adapters and makes "
            "no outbound network call. Set DEMO_MODE=false to attempt the live adapters; "
            "any provider whose optional free credential is unset reports available=false "
            "and is skipped rather than failing the request."
        ),
    }
