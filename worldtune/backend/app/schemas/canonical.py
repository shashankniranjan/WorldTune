"""Canonical provider output models.

Hard rule: **no third-party JSON reaches anything downstream of a provider
adapter.** Every adapter -- real or demo -- returns one of these four models,
so the persistence layer, analytics, ranking and API all depend on WorldTune's
own vocabulary. Swapping CoinGecko for Binance, or Adzuna for RemoteOK, is
then a one-file change.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CanonicalMarketPrice(BaseModel):
    """One OHLCV bar for one asset."""

    symbol: str                      # "BTC", "NVDA"
    asset_class: str = "equity"      # crypto|equity|etf
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    currency: str = "USD"
    source: str = ""


class CanonicalNewsEvent(BaseModel):
    title: str
    summary: str = ""
    url: str = ""
    published_at: datetime
    source: str = ""
    domain: str = ""
    language: str = "en"
    # Sentiment in [-1, 1]. Providers that expose their own tone (GDELT) map it
    # into this range; others fall back to the lexicon in app/analytics/sentiment.py.
    sentiment: float = 0.0
    entities: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    # Provider-supplied lead image (e.g. GDELT's `socialimage`), when present.
    # Free to capture, never fabricated -- absent means None, not a placeholder.
    image_url: Optional[str] = None


class CanonicalJob(BaseModel):
    external_id: str
    title: str
    company: str = ""
    description: str = ""
    location: str = ""
    country: str = ""
    remote: bool = False
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = ""
    url: str = ""
    source: str = ""
    posted_at: datetime


class CanonicalTechEvent(BaseModel):
    name: str                       # "Apache Iceberg"
    title: str = ""
    category: str = ""
    url: str = ""
    source: str = ""
    observed_at: datetime
    stars: float = 0.0
    stars_7d_delta: float = 0.0
    points: float = 0.0
    mentions: float = 0.0
