"""Market data provider interface + implementations.

`MarketDataProvider` is the port -- **unchanged** by the free-data
refactor, so all prediction/evaluation logic stays decoupled from where
prices come from.

Implementations:

  * `SyntheticMarketDataProvider` -- seeded geometric-random-walk OHLCV.
    Deterministic and offline; the default and what every test uses.
  * `BinancePublicMarketProvider` -- **free, no auth**. Binance's public
    `/api/v3/klines` endpoint, real hourly/daily OHLCV for crypto.
  * `StooqMarketProvider` -- **free, no auth**. Stooq's CSV endpoint,
    daily OHLCV for equity indices, commodity futures, FX and US ETFs.
  * `YFinanceMarketDataProvider` -- best-effort, needs the optional
    `yfinance` package; never used by default.

`get_market_data_provider()` maps `settings.market_data_provider` onto one
of these, defaulting to synthetic so nothing needs the network.
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from worldpulse.config import settings
from worldpulse.ingestion import http_utils
from worldpulse.markets.instruments import ASSET_CLASS_ANNUAL_VOL, INSTRUMENTS_BY_SYMBOL

logger = logging.getLogger(__name__)


@dataclass
class Bar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class MarketDataProvider(ABC):
    @abstractmethod
    def get_bars(self, symbol: str, start: datetime, end: datetime, interval: str = "1h") -> list[Bar]:
        ...


def _interval_to_timedelta(interval: str) -> timedelta:
    unit = interval[-1]
    value = int(interval[:-1])
    if unit == "h":
        return timedelta(hours=value)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "d":
        return timedelta(days=value)
    raise ValueError(f"Unsupported interval: {interval}")


def _symbol_seed(symbol: str, base_seed: int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{symbol}".encode()).hexdigest()
    return int(digest[:8], 16)


class SyntheticMarketDataProvider(MarketDataProvider):
    """Deterministic geometric-random-walk OHLCV generator.

    Each symbol gets its own seeded RNG (derived from `base_seed` + symbol
    name) so bars are reproducible across calls/tests, but different
    symbols don't move in lockstep. Volatility is calibrated per asset
    class via `ASSET_CLASS_ANNUAL_VOL`.
    """

    def __init__(self, base_seed: int = 42, base_prices: dict[str, float] | None = None):
        self._base_seed = base_seed
        self._base_prices = base_prices or {}
        self._cache: dict[tuple[str, str], list[Bar]] = {}

    def _base_price(self, symbol: str) -> float:
        if symbol in self._base_prices:
            return self._base_prices[symbol]
        # Deterministic pseudo-realistic base price per symbol.
        seed = _symbol_seed(symbol, self._base_seed)
        return 10.0 + (seed % 50000) / 100.0

    def get_bars(self, symbol: str, start: datetime, end: datetime, interval: str = "1h") -> list[Bar]:
        if end < start:
            return []
        step = _interval_to_timedelta(interval)
        instrument = INSTRUMENTS_BY_SYMBOL.get(symbol)
        asset_class = instrument.asset_class if instrument else "equity_index"
        annual_vol = ASSET_CLASS_ANNUAL_VOL.get(asset_class, 0.20)

        # Generate deterministically from a fixed epoch so that overlapping
        # windows for the same symbol always agree bar-for-bar (important
        # for the no-lookahead tests: prepending/appending data must not
        # change already-generated bars).
        epoch = datetime(2020, 1, 1, tzinfo=start.tzinfo)
        periods_per_year = timedelta(days=365) / step
        per_step_vol = annual_vol / math.sqrt(periods_per_year)

        rng_seed = _symbol_seed(symbol, self._base_seed)
        price = self._base_price(symbol)

        bars: list[Bar] = []
        t = epoch
        idx = 0
        # Walk forward from epoch, generating a fresh deterministic return
        # for each step using a hash-derived RNG, until we reach `start`.
        while t <= end:
            step_rng = random.Random((rng_seed + idx) & 0xFFFFFFFF)
            drift = 0.0
            shock = step_rng.gauss(drift, per_step_vol)
            open_price = price
            close_price = max(0.01, open_price * math.exp(shock))
            high = max(open_price, close_price) * (1 + abs(step_rng.gauss(0, per_step_vol / 3)))
            low = min(open_price, close_price) * (1 - abs(step_rng.gauss(0, per_step_vol / 3)))
            volume = 1000 + step_rng.random() * 5000
            if t >= start:
                bars.append(Bar(
                    symbol=symbol, timestamp=t, open=round(open_price, 4),
                    high=round(high, 4), low=round(low, 4), close=round(close_price, 4),
                    volume=round(volume, 2), source="synthetic",
                ))
            price = close_price
            t += step
            idx += 1
        return bars


class YFinanceMarketDataProvider(MarketDataProvider):
    """Best-effort real market data provider -- NOT used by default.

    Wraps `yfinance` if installed; every call is guarded so a missing
    dependency or network failure degrades to an empty list rather than
    crashing callers.
    """

    def get_bars(self, symbol: str, start: datetime, end: datetime, interval: str = "1h") -> list[Bar]:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            return []
        try:
            df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
            bars = []
            for ts, row in df.iterrows():
                bars.append(Bar(
                    symbol=symbol, timestamp=ts.to_pydatetime(),
                    open=float(row["Open"]), high=float(row["High"]),
                    low=float(row["Low"]), close=float(row["Close"]),
                    volume=float(row["Volume"]), source="yfinance",
                ))
            return bars
        except Exception:
            return []


# --- Free, no-auth real market data ---------------------------------------

#: WorldPulse instrument symbol -> Binance spot trading pair.
BINANCE_SYMBOL_MAP: dict[str, str] = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
}

#: WorldPulse instrument symbol -> Stooq ticker.
#: Stooq uses `^spx`-style index tickers, `<root>.f` for continuous futures,
#: bare pairs for FX and `<ticker>.us` for US-listed ETFs.
STOOQ_SYMBOL_MAP: dict[str, str] = {
    "^GSPC": "^spx",
    "^IXIC": "^ndq",
    "^VIX": "^vix",
    "GC=F": "gc.f",
    "SI=F": "si.f",
    "HG=F": "hg.f",
    "BZ=F": "cb.f",
    "CL=F": "cl.f",
    "NG=F": "ng.f",
    "EURUSD=X": "eurusd",
    "JPY=X": "usdjpy",
    "DX-Y.NYB": "dx.f",
    "SOXX": "soxx.us",
    "XLE": "xle.us",
    "ITA": "ita.us",
    "TLT": "tlt.us",
    "BTC-USD": "btcusd",
    "ETH-USD": "ethusd",
}


class BinancePublicMarketProvider(MarketDataProvider):
    """Binance public klines -- free, no API key, no account.

    Real endpoint:
        GET https://api.binance.com/api/v3/klines
            ?symbol=BTCUSDT&interval=1h&startTime=<ms>&endTime=<ms>&limit=1000

    Response is a JSON array of arrays:
        [[openTime_ms, "open", "high", "low", "close", "volume",
          closeTime_ms, "quoteAssetVolume", numTrades,
          "takerBuyBaseVolume", "takerBuyQuoteVolume", "ignore"], ...]

    Rate limits: Binance uses a weighted IP budget (6000 request-weight per
    minute; a klines call with limit<=100 costs 1, up to 1000 costs 2). It
    returns HTTP 429 with `Retry-After` when exceeded, which the shared
    `http_utils` retry helper honours, and HTTP 418 on a ban.

    Coverage: full spot history back to each pair's listing date (BTCUSDT
    from 2017-08). Crypto only -- for equities/commodities/FX use
    `StooqMarketProvider`.
    """

    BASE_URL = "https://api.binance.com/api/v3/klines"
    #: Binance caps one klines response at 1000 rows.
    MAX_LIMIT = 1000

    #: WorldPulse interval -> Binance interval. Binance accepts
    #: 1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1M.
    INTERVAL_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "12h": "12h",
        "1d": "1d", "1w": "1w",
    }

    def __init__(self, client: Optional[httpx.Client] = None,
                 symbol_map: dict[str, str] | None = None) -> None:
        self._client = client
        self._symbol_map = symbol_map if symbol_map is not None else BINANCE_SYMBOL_MAP

    def supports(self, symbol: str) -> bool:
        return symbol in self._symbol_map

    def get_bars(self, symbol: str, start: datetime, end: datetime,
                 interval: str = "1h") -> list[Bar]:
        pair = self._symbol_map.get(symbol)
        if pair is None:
            # Not a crypto pair Binance lists: return nothing rather than
            # guessing, so the caller can fall back to another provider.
            logger.debug("binance: no pair mapping for %s", symbol)
            return []
        binance_interval = self.INTERVAL_MAP.get(interval)
        if binance_interval is None:
            logger.warning("binance: unsupported interval %r for %s", interval, symbol)
            return []

        start = _as_utc(start)
        end = _as_utc(end)
        step = _interval_to_timedelta(interval)
        bars: list[Bar] = []
        cursor = start
        # Page forward: one response holds at most MAX_LIMIT candles.
        while cursor < end:
            params = {
                "symbol": pair,
                "interval": binance_interval,
                "startTime": int(cursor.timestamp() * 1000),
                "endTime": int(end.timestamp() * 1000),
                "limit": self.MAX_LIMIT,
            }
            try:
                rows = http_utils.http_get_json(self.BASE_URL, params=params, client=self._client)
            except Exception as exc:  # noqa: BLE001 - degrade, never crash the pipeline
                logger.warning("binance: klines %s failed: %s", pair, exc)
                break
            if not isinstance(rows, list) or not rows:
                break
            for row in rows:
                bar = _binance_row_to_bar(symbol, row)
                if bar is not None:
                    bars.append(bar)
            if len(rows) < self.MAX_LIMIT:
                break
            last_open_ms = rows[-1][0]
            cursor = datetime.fromtimestamp(float(last_open_ms) / 1000.0, tz=timezone.utc) + step
        return bars


class StooqMarketProvider(MarketDataProvider):
    """Stooq CSV download -- free, no API key, no account.

    Real endpoint:
        GET https://stooq.com/q/d/l/?s=<ticker>&i=d&d1=YYYYMMDD&d2=YYYYMMDD

    Response is a CSV with header `Date,Open,High,Low,Close,Volume` (one
    row per session). An unknown ticker returns the literal body
    `No data`.

    Limitations, stated honestly: Stooq's CSV download is **daily only**
    (`i=d`; weekly/monthly also exist, intraday does not), so a request for
    a `1h` interval returns daily bars and logs a warning -- WorldPulse's
    1h/4h/8h/12h prediction horizons cannot be evaluated from Stooq data.
    Use Binance (crypto, real hourly) or the synthetic provider for
    sub-daily work. Rate limits are undocumented; Stooq throttles
    aggressive scraping, so poll a few symbols at a time and cache.

    Coverage: multi-decade daily history for indices, continuous futures,
    FX pairs and US ETFs.
    """

    BASE_URL = "https://stooq.com/q/d/l/"

    def __init__(self, client: Optional[httpx.Client] = None,
                 symbol_map: dict[str, str] | None = None) -> None:
        self._client = client
        self._symbol_map = symbol_map if symbol_map is not None else STOOQ_SYMBOL_MAP

    def supports(self, symbol: str) -> bool:
        return symbol in self._symbol_map

    def get_bars(self, symbol: str, start: datetime, end: datetime,
                 interval: str = "1h") -> list[Bar]:
        ticker = self._symbol_map.get(symbol)
        if ticker is None:
            logger.debug("stooq: no ticker mapping for %s", symbol)
            return []
        if interval != "1d":
            logger.warning(
                "stooq: only daily bars are available (requested %r for %s); "
                "returning daily data", interval, symbol,
            )

        start = _as_utc(start)
        end = _as_utc(end)
        params = {
            "s": ticker,
            "i": "d",
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
        }
        try:
            body = http_utils.http_get_text(self.BASE_URL, params=params, client=self._client)
        except Exception as exc:  # noqa: BLE001
            logger.warning("stooq: download for %s (%s) failed: %s", symbol, ticker, exc)
            return []
        return parse_stooq_csv(symbol, body)


def parse_stooq_csv(symbol: str, body: str) -> list[Bar]:
    """Parse a Stooq daily CSV body into `Bar`s."""
    body = (body or "").strip()
    if not body or body.lower().startswith("no data"):
        return []
    reader = csv.DictReader(io.StringIO(body))
    bars: list[Bar] = []
    for row in reader:
        raw_date = (row.get("Date") or "").strip()
        if not raw_date:
            continue
        try:
            timestamp = datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        try:
            open_price = float(row["Open"])
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            volume = float(row.get("Volume") or 0.0)
        except ValueError:
            volume = 0.0
        bars.append(Bar(symbol=symbol, timestamp=timestamp, open=open_price, high=high,
                        low=low, close=close, volume=volume, source="stooq"))
    bars.sort(key=lambda b: b.timestamp)
    return bars


class CompositeMarketDataProvider(MarketDataProvider):
    """Try each wrapped provider in order until one returns bars.

    Lets a free-mode deployment use Binance for crypto, Stooq for
    everything else, and fall back to the synthetic generator for symbols
    neither covers -- without the prediction layer knowing.
    """

    def __init__(self, providers: list[MarketDataProvider]):
        self._providers = list(providers)

    def get_bars(self, symbol: str, start: datetime, end: datetime,
                 interval: str = "1h") -> list[Bar]:
        for provider in self._providers:
            supports = getattr(provider, "supports", None)
            if callable(supports) and not supports(symbol):
                continue
            bars = provider.get_bars(symbol, start, end, interval=interval)
            if bars:
                return bars
        return []


def get_market_data_provider(name: str | None = None, seed: int | None = None) -> MarketDataProvider:
    """Resolve `MARKET_DATA_PROVIDER` to an implementation.

    Defaults to `synthetic`, so nothing in the default configuration needs
    network access or an API key.
    """
    choice = (name or settings.market_data_provider or "synthetic").strip().lower()
    base_seed = settings.random_seed if seed is None else seed
    synthetic = SyntheticMarketDataProvider(base_seed=base_seed)
    if choice == "binance":
        return CompositeMarketDataProvider([BinancePublicMarketProvider(), synthetic])
    if choice == "stooq":
        return CompositeMarketDataProvider([StooqMarketProvider(), synthetic])
    if choice == "free":
        # Binance for crypto, Stooq for everything else it covers,
        # synthetic for the remainder.
        return CompositeMarketDataProvider([
            BinancePublicMarketProvider(), StooqMarketProvider(), synthetic,
        ])
    if choice == "yfinance":
        return CompositeMarketDataProvider([YFinanceMarketDataProvider(), synthetic])
    if choice != "synthetic":
        logger.warning("unknown MARKET_DATA_PROVIDER=%r; using synthetic", choice)
    return synthetic


def _binance_row_to_bar(symbol: str, row: object) -> Bar | None:
    if not isinstance(row, (list, tuple)) or len(row) < 6:
        return None
    try:
        timestamp = datetime.fromtimestamp(float(row[0]) / 1000.0, tz=timezone.utc)
        return Bar(
            symbol=symbol,
            timestamp=timestamp,
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            source="binance",
        )
    except (TypeError, ValueError, OSError):
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
