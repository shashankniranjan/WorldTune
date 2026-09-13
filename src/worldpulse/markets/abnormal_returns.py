"""Abnormal (volatility-normalized) return computation.

normalized_move = event_return / baseline_volatility

`baseline_volatility` is the rolling standard deviation of per-bar simple
returns computed strictly from bars with timestamp < event_time (never
using the event window itself or anything after it), which keeps this
point-in-time causal.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from worldpulse.ingestion.markets import Bar
from worldpulse.markets.returns import simple_return


def rolling_baseline_volatility(
    bars: list[Bar], event_time: datetime, lookback_hours: float = 24 * 14, min_observations: int = 8
) -> float | None:
    """Stdev of consecutive-bar simple returns strictly before `event_time`."""
    window_start = event_time - timedelta(hours=lookback_hours)
    history = sorted(
        [b for b in bars if window_start <= b.timestamp < event_time],
        key=lambda b: b.timestamp,
    )
    if len(history) < min_observations + 1:
        return None
    rets = [
        simple_return(history[i].close, history[i + 1].close)
        for i in range(len(history) - 1)
    ]
    if len(rets) < min_observations:
        return None
    vol = statistics.pstdev(rets)
    return vol if vol > 0 else None


def abnormal_return(event_return: float | None, baseline_volatility: float | None) -> float | None:
    if event_return is None or baseline_volatility is None or baseline_volatility == 0:
        return None
    return event_return / baseline_volatility


def compute_abnormal_returns(
    bars: list[Bar], event_time: datetime, window_returns: dict[str, float | None]
) -> dict[str, float | None]:
    """Normalize each post-event return in `window_returns` by baseline vol."""
    baseline_vol = rolling_baseline_volatility(bars, event_time)
    result: dict[str, float | None] = {}
    for key, ret in window_returns.items():
        if key.startswith("post_"):
            result[key] = abnormal_return(ret, baseline_vol)
    return result
