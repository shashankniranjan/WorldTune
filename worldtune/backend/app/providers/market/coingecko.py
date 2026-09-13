"""CoinGecko market data adapter -- free, no API key.

Endpoints used (both public, keyless, on the free tier):

  * OHLC bars:
      GET https://api.coingecko.com/api/v3/coins/{id}/ohlc?vs_currency=usd&days=90
      -> [[ms_epoch, open, high, low, close], ...]
    CoinGecko's granularity is determined by `days` (daily candles once
    days > 30), which is exactly the resolution the trend engine wants.

  * Volume (the OHLC endpoint does not carry it):
      GET https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=90&interval=daily
      -> {"prices": [[ms, p], ...], "total_volumes": [[ms, v], ...]}

    The two series are merged on UTC calendar date. A bar whose date has no
    matching volume point keeps volume 0.0 rather than being dropped -- losing
    a price bar to a missing volume would silently corrupt return series.

Rate limits: the keyless tier is roughly 10-30 calls/minute. WorldTune issues
two calls per asset per refresh for a handful of assets, which sits inside
that budget; `app.providers.http` still backs off on 429 with `Retry-After`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.providers.base import MarketDataProvider
from app.providers.http import ProviderHTTPError, http_get_json
from app.schemas.canonical import CanonicalMarketPrice

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"

# WorldTune symbol -> CoinGecko coin id.
COIN_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


class CoinGeckoProvider(MarketDataProvider):
    name = "coingecko"
    is_live = True

    def __init__(self, client: Optional[httpx.Client] = None,
                 coin_ids: dict[str, str] | None = None):
        self._client = client
        self._coin_ids = coin_ids or COIN_IDS

    def is_available(self) -> bool:
        return True  # keyless

    def supported_symbols(self) -> list[str]:
        return list(self._coin_ids)

    # -- fetch ---------------------------------------------------------------
    def fetch_prices(self, symbols: list[str], *, days: int = 90) -> list[CanonicalMarketPrice]:
        out: list[CanonicalMarketPrice] = []
        for symbol in symbols:
            coin_id = self._coin_ids.get(symbol.upper())
            if not coin_id:
                continue
            try:
                ohlc = http_get_json(
                    f"{BASE_URL}/coins/{coin_id}/ohlc",
                    params={"vs_currency": "usd", "days": str(days)},
                    client=self._client,
                )
                chart = http_get_json(
                    f"{BASE_URL}/coins/{coin_id}/market_chart",
                    params={"vs_currency": "usd", "days": str(days), "interval": "daily"},
                    client=self._client,
                )
            except ProviderHTTPError as exc:
                logger.warning("coingecko fetch failed for %s: %s", symbol, exc)
                continue
            out.extend(self.parse(symbol.upper(), ohlc, chart))
        return out

    # -- parsing (pure; unit-tested against fixtures) ------------------------
    @staticmethod
    def parse(symbol: str, ohlc: list, chart: dict) -> list[CanonicalMarketPrice]:
        volumes = _volume_by_date(chart)
        bars: list[CanonicalMarketPrice] = []
        for row in ohlc or []:
            if not isinstance(row, (list, tuple)) or len(row) < 5:
                continue
            ts = _from_ms(row[0])
            bars.append(
                CanonicalMarketPrice(
                    symbol=symbol,
                    asset_class="crypto",
                    timestamp=ts,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=volumes.get(ts.date().isoformat(), 0.0),
                    currency="USD",
                    source="coingecko",
                )
            )
        return bars


def _from_ms(ms: float) -> datetime:
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)


def _volume_by_date(chart: dict) -> dict[str, float]:
    """Collapse `total_volumes` to one value per UTC date (last wins)."""
    out: dict[str, float] = {}
    for point in (chart or {}).get("total_volumes", []) or []:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        out[_from_ms(point[0]).date().isoformat()] = float(point[1])
    return out
