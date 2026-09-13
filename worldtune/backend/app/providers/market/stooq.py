"""Stooq equities/ETF adapter -- free daily OHLCV CSV, no API key.

Endpoint:
    GET https://stooq.com/q/d/l/?s=<symbol>.us&i=d
    -> CSV: Date,Open,High,Low,Close,Volume

Chosen over Yahoo Finance's undocumented `query1.finance.yahoo.com/v8/...`
JSON because Stooq publishes a stable, documented CSV URL that needs no
cookie/crumb dance. Same idea as WorldPulse's equities feed, re-implemented
here so the two products share no code.

Quirks handled below, all of which are real and will bite otherwise:
  * an unknown symbol returns the literal body "No data" with HTTP 200;
  * rows are oldest-first and the file may contain a trailing blank line;
  * missing cells are rendered as "N/A" (notably Volume on some ETFs).
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, time, timezone
from typing import Optional

import httpx

from app.providers.base import MarketDataProvider
from app.providers.http import ProviderHTTPError, http_get_text
from app.schemas.canonical import CanonicalMarketPrice

logger = logging.getLogger(__name__)

BASE_URL = "https://stooq.com/q/d/l/"

# Equity/ETF universe relevant to the demo persona's sectors (AI, technology).
DEFAULT_TICKERS = ("QQQ", "NVDA", "MSFT", "GOOGL", "AMD", "SNOW")


class StooqProvider(MarketDataProvider):
    name = "stooq"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client

    def is_available(self) -> bool:
        return True  # keyless

    def supported_symbols(self) -> list[str]:
        return list(DEFAULT_TICKERS)

    def fetch_prices(self, symbols: list[str], *, days: int = 90) -> list[CanonicalMarketPrice]:
        out: list[CanonicalMarketPrice] = []
        for symbol in symbols:
            try:
                body = http_get_text(
                    BASE_URL,
                    params={"s": f"{symbol.lower()}.us", "i": "d"},
                    client=self._client,
                )
            except ProviderHTTPError as exc:
                logger.warning("stooq fetch failed for %s: %s", symbol, exc)
                continue
            bars = self.parse(symbol.upper(), body)
            out.extend(bars[-days:] if days else bars)
        return out

    @staticmethod
    def parse(symbol: str, body: str) -> list[CanonicalMarketPrice]:
        """Parse a Stooq daily CSV into canonical bars (oldest-first preserved)."""
        text = (body or "").strip()
        if not text or text.lower().startswith("no data"):
            return []
        reader = csv.DictReader(io.StringIO(text))
        bars: list[CanonicalMarketPrice] = []
        for row in reader:
            raw_date = (row.get("Date") or "").strip()
            if not raw_date:
                continue
            try:
                day = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                continue
            close = _num(row.get("Close"))
            if close is None:
                continue  # a bar without a close is unusable
            bars.append(
                CanonicalMarketPrice(
                    symbol=symbol,
                    asset_class="equity",
                    timestamp=datetime.combine(day, time(0, 0), tzinfo=timezone.utc),
                    open=_num(row.get("Open")) or close,
                    high=_num(row.get("High")) or close,
                    low=_num(row.get("Low")) or close,
                    close=close,
                    volume=_num(row.get("Volume")) or 0.0,
                    currency="USD",
                    source="stooq",
                )
            )
        return bars


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.upper() in {"N/A", "NA", "-"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None
