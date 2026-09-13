"""Event-window return computation.

For an event at time T, we compute simple returns over fixed pre-event
windows (-24h, -8h, -1h -> 0) and fixed post-event horizons (0 -> +1h/+4h/
+8h/+12h/+24h). Every lookup uses only bars whose timestamp is <= the
window's own end -- callers must pass an `as_of` cutoff that is never later
than (T + horizon) so no future information leaks into a return computed
for an earlier horizon.

Lookups use `bisect` against a pre-sorted timestamp list so this stays
cheap even when called once per (symbol, historical-event) pair during
prediction generation -- see `prediction/predictor.py`, which sorts each
symbol's bars once and reuses that sorted list across many events.
"""
from __future__ import annotations

import bisect
from datetime import datetime, timedelta

from worldpulse.ingestion.markets import Bar

PRE_WINDOWS_HOURS: list[float] = [24, 8, 1]
POST_HORIZONS_HOURS: list[float] = [1, 4, 8, 12, 24]


def _nearest_bar_at_or_before(sorted_bars: list[Bar], sorted_timestamps: list[datetime], target: datetime) -> Bar | None:
    idx = bisect.bisect_right(sorted_timestamps, target) - 1
    if idx < 0:
        return None
    return sorted_bars[idx]


def _nearest_bar_at_or_after(sorted_bars: list[Bar], sorted_timestamps: list[datetime], target: datetime) -> Bar | None:
    idx = bisect.bisect_left(sorted_timestamps, target)
    if idx >= len(sorted_bars):
        return None
    return sorted_bars[idx]


def simple_return(price_from: float, price_to: float) -> float:
    if price_from == 0:
        return 0.0
    return (price_to - price_from) / price_from


def compute_event_window_returns(
    bars: list[Bar], event_time: datetime, presorted: bool = False
) -> dict[str, float | None]:
    """Compute pre-event and post-event returns around `event_time`.

    `bars` should already be filtered to timestamp <= (event_time + max
    horizon actually needed by the caller) -- this function itself performs
    no filtering by "now", it only picks the right bars out of what it's
    given, so causality is enforced by what the caller passes in.

    If the caller already has `bars` sorted by timestamp ascending, pass
    `presorted=True` to skip re-sorting on every call (important for
    performance when this is called once per historical analogue).

    Returns a dict with keys like "pre_24h", "pre_8h", "pre_1h",
    "post_1h", "post_4h", "post_8h", "post_12h", "post_24h".
    A value is None if there is insufficient bar coverage.
    """
    sorted_bars = bars if presorted else sorted(bars, key=lambda b: b.timestamp)
    sorted_timestamps = [b.timestamp for b in sorted_bars]
    result: dict[str, float | None] = {}

    t0_bar = _nearest_bar_at_or_before(sorted_bars, sorted_timestamps, event_time)
    if t0_bar is None:
        t0_bar = _nearest_bar_at_or_after(sorted_bars, sorted_timestamps, event_time)

    for hours in PRE_WINDOWS_HOURS:
        window_start = event_time - timedelta(hours=hours)
        start_bar = _nearest_bar_at_or_before(sorted_bars, sorted_timestamps, window_start)
        if start_bar is None or t0_bar is None:
            result[f"pre_{int(hours)}h"] = None
        else:
            result[f"pre_{int(hours)}h"] = simple_return(start_bar.close, t0_bar.close)

    for hours in POST_HORIZONS_HOURS:
        window_end = event_time + timedelta(hours=hours)
        end_bar = _nearest_bar_at_or_before(sorted_bars, sorted_timestamps, window_end)
        if end_bar is None or t0_bar is None or end_bar.timestamp <= t0_bar.timestamp:
            result[f"post_{int(hours)}h"] = None
        else:
            result[f"post_{int(hours)}h"] = simple_return(t0_bar.close, end_bar.close)

    return result


def sort_bars(bars: list[Bar]) -> list[Bar]:
    return sorted(bars, key=lambda b: b.timestamp)


def get_reference_close(bars: list[Bar], at_or_before: datetime, presorted: bool = False) -> float | None:
    sorted_bars = bars if presorted else sorted(bars, key=lambda b: b.timestamp)
    sorted_timestamps = [b.timestamp for b in sorted_bars]
    bar = _nearest_bar_at_or_before(sorted_bars, sorted_timestamps, at_or_before)
    return bar.close if bar else None
