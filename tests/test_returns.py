from datetime import datetime, timedelta, timezone

from worldpulse.ingestion.markets import Bar
from worldpulse.markets.returns import compute_event_window_returns, simple_return


def make_bar(symbol, dt, close):
    return Bar(symbol=symbol, timestamp=dt, open=close, high=close, low=close, close=close, volume=100, source="test")


def test_simple_return_basic():
    assert simple_return(100.0, 110.0) == 0.10
    assert simple_return(100.0, 90.0) == -0.10
    assert simple_return(0.0, 100.0) == 0.0


def test_event_window_returns_hand_computed():
    event_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    bars = [
        make_bar("X", event_time - timedelta(hours=24), 100.0),
        make_bar("X", event_time - timedelta(hours=8), 105.0),
        make_bar("X", event_time - timedelta(hours=1), 108.0),
        make_bar("X", event_time, 110.0),
        make_bar("X", event_time + timedelta(hours=1), 112.0),
        make_bar("X", event_time + timedelta(hours=4), 115.0),
        make_bar("X", event_time + timedelta(hours=8), 100.0),
        make_bar("X", event_time + timedelta(hours=12), 120.0),
        make_bar("X", event_time + timedelta(hours=24), 121.0),
    ]

    result = compute_event_window_returns(bars, event_time)

    assert result["pre_24h"] == simple_return(100.0, 110.0)
    assert result["pre_8h"] == simple_return(105.0, 110.0)
    assert result["pre_1h"] == simple_return(108.0, 110.0)

    assert result["post_1h"] == simple_return(110.0, 112.0)
    assert result["post_4h"] == simple_return(110.0, 115.0)
    assert result["post_8h"] == simple_return(110.0, 100.0)
    assert result["post_12h"] == simple_return(110.0, 120.0)
    assert result["post_24h"] == simple_return(110.0, 121.0)


def test_event_window_returns_missing_coverage_is_none():
    event_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    bars = [make_bar("X", event_time, 100.0)]
    result = compute_event_window_returns(bars, event_time)
    assert result["pre_24h"] is None
    assert result["post_24h"] is None
