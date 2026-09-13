"""Trend engine -- real time-series statistics, NOT an LLM.

This module is where "is it heating up or cooling down?" is answered, and it
answers with arithmetic that a user can check: percentage change over a
window, a second difference for acceleration, a moving average, a z-score.
Every function here is pure -- it takes a series and returns numbers -- so
each one is unit-tested against hand-computed fixtures.

Applies uniformly to job-posting velocity, skill-mention growth, news volume,
sentiment change, price momentum, trading volume and GitHub star velocity:
they are all just series, which is the point of normalizing everything to
canonical models first.

Conventions, chosen once so every caller means the same thing:
  * series are ordered oldest -> newest;
  * "change" is *fractional* (0.07 == +7%), not percentage points, except
    where a function name says `_pct`;
  * an insufficient or degenerate window returns 0.0, never NaN -- NaN
    propagating into a score is the classic way a dashboard silently shows
    nonsense.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


@dataclass
class TrendMetrics:
    """The standard trend bundle computed for every tracked series."""

    latest: float = 0.0
    change_7d: float = 0.0
    change_30d: float = 0.0
    acceleration: float = 0.0
    ma_7: float = 0.0
    ma_30: float = 0.0
    zscore: float = 0.0
    slope: float = 0.0
    direction: str = "stable"   # rising|stable|falling
    n_observations: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# --- primitives --------------------------------------------------------------

def _clean(values) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return arr
    return arr[np.isfinite(arr)]


def pct_change_over(values, window: int) -> float:
    """Fractional change between the value `window` steps back and the latest.

    Returns 0.0 when the series is too short or the reference value is zero
    (an undefined ratio is not a 100% move).
    """
    arr = _clean(values)
    if arr.size < window + 1:
        return 0.0
    prior = arr[-(window + 1)]
    if prior == 0:
        return 0.0
    return float(arr[-1] / prior - 1.0)


def moving_average(values, window: int) -> float:
    arr = _clean(values)
    if arr.size == 0:
        return 0.0
    return float(arr[-min(window, arr.size):].mean())


def acceleration(values, window: int = 7) -> float:
    """Second derivative: change in the last `window` minus change in the one before.

    Positive means the series is not merely rising but rising *faster* --
    which is the difference between "AI hiring is up" and "AI hiring is
    taking off", and is the quantity a user actually wants surfaced.
    """
    arr = _clean(values)
    if arr.size < 2 * window + 1:
        return 0.0
    recent = arr[-1] - arr[-(window + 1)]
    prior = arr[-(window + 1)] - arr[-(2 * window + 1)]
    return float(recent - prior)


def zscore(values, window: int = 30) -> float:
    """Z-score of the latest observation against the trailing `window`.

    Uses the sample stdev of the window *excluding* nothing (the latest point
    is part of its own reference window, which is standard for an anomaly
    z-score on a short series) and returns 0.0 for a constant window rather
    than dividing by zero.
    """
    arr = _clean(values)
    if arr.size < 3:
        return 0.0
    tail = arr[-min(window, arr.size):]
    sd = float(tail.std(ddof=1))
    if sd == 0.0 or not np.isfinite(sd):
        return 0.0
    return float((arr[-1] - tail.mean()) / sd)


def linear_slope(values, window: int = 14) -> float:
    """OLS slope per step over the trailing window (units of the series)."""
    arr = _clean(values)
    if arr.size < 3:
        return 0.0
    tail = arr[-min(window, arr.size):]
    x = np.arange(tail.size, dtype=float)
    slope = float(np.polyfit(x, tail, 1)[0])
    return slope if np.isfinite(slope) else 0.0


def ewma_momentum(values, span: int = 10) -> float:
    """Normalized EWMA momentum: (EWMA_fast - EWMA_slow) / EWMA_slow.

    A scale-free trend measure -- comparable between a $61,000 asset and a
    0.14 skill-share -- which is exactly what a cross-domain ranker needs.
    """
    arr = _clean(values)
    if arr.size < 3:
        return 0.0
    series = pd.Series(arr)
    fast = float(series.ewm(span=span, adjust=False).mean().iloc[-1])
    slow = float(series.ewm(span=span * 3, adjust=False).mean().iloc[-1])
    if slow == 0 or not np.isfinite(slow):
        return 0.0
    return float((fast - slow) / abs(slow))


def classify_direction(change: float, *, threshold: float = 0.02) -> str:
    if change > threshold:
        return "rising"
    if change < -threshold:
        return "falling"
    return "stable"


# --- bundle ------------------------------------------------------------------

def compute_trend(values, *, short: int = 7, long: int = 30) -> TrendMetrics:
    """The standard bundle for a daily series (oldest -> newest)."""
    arr = _clean(values)
    if arr.size == 0:
        return TrendMetrics()
    change_7d = pct_change_over(arr, short)
    return TrendMetrics(
        latest=float(arr[-1]),
        change_7d=change_7d,
        change_30d=pct_change_over(arr, long),
        acceleration=acceleration(arr, short),
        ma_7=moving_average(arr, short),
        ma_30=moving_average(arr, long),
        zscore=zscore(arr, long),
        slope=linear_slope(arr, min(long, 14)),
        direction=classify_direction(change_7d),
        n_observations=int(arr.size),
    )


def returns_from_prices(closes) -> np.ndarray:
    """Simple daily returns. Length n-1; a zero prior price yields a 0.0 return."""
    arr = _clean(closes)
    if arr.size < 2:
        return np.array([], dtype=float)
    prior = arr[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        rets = np.where(prior == 0, 0.0, arr[1:] / np.where(prior == 0, 1.0, prior) - 1.0)
    return np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0)


def realized_volatility(closes, window: int = 30) -> float:
    """Annualized stdev of daily returns over the window (365-day convention)."""
    rets = returns_from_prices(closes)
    if rets.size < 3:
        return 0.0
    tail = rets[-min(window, rets.size):]
    return float(tail.std(ddof=1) * np.sqrt(365.0))


def daily_counts(timestamps: list[datetime], *, as_of: datetime,
                 days: int = 60) -> list[float]:
    """Bucket event timestamps into a dense daily count series ending at `as_of`.

    Dense is the operative word: days with no events must appear as 0, not be
    missing, or "change over 7 days" silently becomes "change over the last 7
    days that happened to have news".
    """
    start = (as_of - timedelta(days=days - 1)).date()
    buckets = {start + timedelta(days=i): 0.0 for i in range(days)}
    for ts in timestamps:
        day = ts.date()
        if day in buckets:
            buckets[day] += 1.0
    return [buckets[k] for k in sorted(buckets)]


def daily_means(timestamps: list[datetime], values: list[float], *, as_of: datetime,
                days: int = 60, fill: float = 0.0) -> list[float]:
    """Daily mean of `values` bucketed by timestamp; empty days take `fill`.

    Used for sentiment, where the mean of an empty day is genuinely "no
    information" (0.0 == neutral) rather than zero sentiment.
    """
    start = (as_of - timedelta(days=days - 1)).date()
    sums: dict = {start + timedelta(days=i): [0.0, 0] for i in range(days)}
    for ts, val in zip(timestamps, values):
        day = ts.date()
        if day in sums:
            sums[day][0] += float(val)
            sums[day][1] += 1
    out = []
    for key in sorted(sums):
        total, count = sums[key]
        out.append(total / count if count else fill)
    return out
