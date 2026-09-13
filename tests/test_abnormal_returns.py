from datetime import datetime, timedelta, timezone

from worldpulse.ingestion.markets import Bar
from worldpulse.markets.abnormal_returns import abnormal_return, compute_abnormal_returns, rolling_baseline_volatility


def make_bar(symbol, dt, close):
    return Bar(symbol=symbol, timestamp=dt, open=close, high=close, low=close, close=close, volume=100, source="test")


def test_abnormal_return_normalization():
    assert abnormal_return(0.02, 0.01) == 2.0
    assert abnormal_return(None, 0.01) is None
    assert abnormal_return(0.02, None) is None
    assert abnormal_return(0.02, 0.0) is None


def test_rolling_baseline_volatility_uses_only_prior_bars():
    event_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    bars = []
    # 20 hourly bars before the event with alternating +1%/-1% returns.
    price = 100.0
    for i in range(20, 0, -1):
        bars.append(make_bar("X", event_time - timedelta(hours=i), price))
        price = price * (1.01 if i % 2 == 0 else 0.99)
    # A huge future move should NOT affect the baseline volatility.
    bars.append(make_bar("X", event_time, price))
    bars.append(make_bar("X", event_time + timedelta(hours=1), price * 10))

    vol_with_future = rolling_baseline_volatility(bars, event_time, lookback_hours=48, min_observations=8)

    # Remove the future bars entirely and confirm the baseline is identical.
    bars_no_future = [b for b in bars if b.timestamp < event_time]
    vol_without_future = rolling_baseline_volatility(bars_no_future, event_time, lookback_hours=48, min_observations=8)

    assert vol_with_future == vol_without_future
    assert vol_with_future is not None
    assert vol_with_future > 0


def test_compute_abnormal_returns_only_normalizes_post_keys():
    event_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    bars = [make_bar("X", event_time - timedelta(hours=i), 100.0 + (i % 3)) for i in range(1, 20)]
    window_returns = {"pre_1h": 0.01, "post_1h": 0.02, "post_4h": None}
    result = compute_abnormal_returns(bars, event_time, window_returns)
    assert "pre_1h" not in result
    assert "post_1h" in result
    assert result["post_4h"] is None
