"""Deterministic demo market data -- the DEMO_MODE=true default path.

This is *seeded simulation*, clearly labelled as such (`is_live = False`,
`source="demo:market"`), never a real feed wearing a costume. The generator
is a geometric random walk with a per-asset drift, volatility and
volume profile, driven by a seeded `numpy.random.Generator` so the same
symbol always produces the same series. That matters for three reasons:

  * the trend engine gets genuinely non-trivial input (real returns, real
    variance) instead of a flat line, so 7d/30d/acceleration are meaningful;
  * tests can assert on exact values;
  * a demo shown twice looks the same twice.

Drifts are chosen to make the persona's story legible (BTC and NVDA trending,
MSFT flat-ish, AMD choppy), not to predict anything about the real assets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

import numpy as np

from app.providers.base import MarketDataProvider
from app.schemas.canonical import CanonicalMarketPrice


@dataclass(frozen=True)
class DemoAssetSpec:
    symbol: str
    name: str
    asset_class: str
    sector: str
    start_price: float
    annual_drift: float      # e.g. 0.45 == +45%/yr expected drift
    daily_vol: float         # stdev of daily log return
    base_volume: float
    seed: int


DEMO_ASSETS: tuple[DemoAssetSpec, ...] = (
    DemoAssetSpec("BTC",   "Bitcoin",    "crypto", "crypto",     61250.0, 0.55, 0.031, 2.8e10, 101),
    DemoAssetSpec("ETH",   "Ethereum",   "crypto", "crypto",      3120.0, 0.38, 0.038, 1.4e10, 102),
    DemoAssetSpec("NVDA",  "NVIDIA",     "equity", "AI",           118.4, 0.72, 0.030, 3.1e8,  103),
    DemoAssetSpec("MSFT",  "Microsoft",  "equity", "technology",   421.0, 0.14, 0.013, 2.0e7,  104),
    DemoAssetSpec("GOOGL", "Alphabet",   "equity", "technology",   178.5, 0.18, 0.016, 2.6e7,  105),
    DemoAssetSpec("AMD",   "AMD",        "equity", "AI",           152.7, 0.09, 0.034, 5.4e7,  106),
    DemoAssetSpec("QQQ",   "Nasdaq 100", "etf",    "technology",   486.3, 0.16, 0.011, 4.1e7,  107),
    DemoAssetSpec("SNOW",  "Snowflake",  "equity", "technology",   131.9, -0.12, 0.029, 4.9e6, 108),
)

DEMO_ASSETS_BY_SYMBOL = {a.symbol: a for a in DEMO_ASSETS}


class DemoMarketDataProvider(MarketDataProvider):
    name = "demo:market"
    is_live = False

    def __init__(self, as_of: datetime | None = None):
        # Anchoring the walk to a date makes the series stable within a run and
        # lets tests pin `as_of` for exact assertions.
        self._as_of = as_of or datetime.now(timezone.utc)

    def is_available(self) -> bool:
        return True

    def supported_symbols(self) -> list[str]:
        return [a.symbol for a in DEMO_ASSETS]

    def asset_spec(self, symbol: str) -> DemoAssetSpec | None:
        return DEMO_ASSETS_BY_SYMBOL.get(symbol.upper())

    def fetch_prices(self, symbols: list[str], *, days: int = 90) -> list[CanonicalMarketPrice]:
        out: list[CanonicalMarketPrice] = []
        for symbol in symbols:
            spec = DEMO_ASSETS_BY_SYMBOL.get(symbol.upper())
            if spec is None:
                continue
            out.extend(self._simulate(spec, days))
        return out

    def _simulate(self, spec: DemoAssetSpec, days: int) -> list[CanonicalMarketPrice]:
        rng = np.random.default_rng(spec.seed)
        mu = spec.annual_drift / 365.0
        sigma = spec.daily_vol
        # Log-return walk; the -sigma^2/2 term keeps the *expected* price path
        # equal to the stated drift rather than drifting high from convexity.
        returns = rng.normal(loc=mu - 0.5 * sigma**2, scale=sigma, size=days)
        closes = spec.start_price * np.exp(np.cumsum(returns))

        end_day = self._as_of.date()
        bars: list[CanonicalMarketPrice] = []
        prev_close = spec.start_price
        for i, close in enumerate(closes):
            day = end_day - timedelta(days=days - 1 - i)
            # Crypto trades every day; equities skip weekends.
            if spec.asset_class != "crypto" and day.weekday() >= 5:
                continue
            close = float(close)
            intraday = abs(rng.normal(0.0, sigma * 0.6))
            high = max(prev_close, close) * (1.0 + intraday)
            low = min(prev_close, close) * (1.0 - intraday)
            # Volume co-moves with the size of the day's move -- big days are
            # high-volume days, which is what makes the volume z-score feature
            # carry any information at all.
            move = abs(close / prev_close - 1.0)
            volume = spec.base_volume * float(np.exp(rng.normal(0.0, 0.25))) * (1.0 + 6.0 * move)
            bars.append(
                CanonicalMarketPrice(
                    symbol=spec.symbol,
                    asset_class=spec.asset_class,
                    timestamp=datetime.combine(day, time(0, 0), tzinfo=timezone.utc),
                    open=round(prev_close, 4),
                    high=round(high, 4),
                    low=round(low, 4),
                    close=round(close, 4),
                    volume=round(volume, 2),
                    currency="USD",
                    source="demo:market",
                )
            )
            prev_close = close
        return bars
