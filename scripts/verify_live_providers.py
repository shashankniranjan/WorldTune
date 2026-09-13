#!/usr/bin/env python3
"""Live reachability check for WorldPulse's free data providers.

**Run this on a machine with normal internet access.** It makes real
network calls; the automated test suite deliberately does not (it drives
every adapter through `httpx.MockTransport` with fixture payloads instead,
so CI stays deterministic and offline). This script is the complement:
it proves the endpoints, query parameters and response schemas the
adapters assume are actually live.

Checks, in order:

  1. **GDELT DOC 2.0** -- `api.gdeltproject.org` article search
  2. **USGS** -- both the FDSN historical event query and the summary feed
  3. **Binance public klines** -- `api.binance.com`, no auth
  and, as extra credit (still keyless):
  4. **NASA EONET v3**
  5. **GDACS EVENTS4APP**
  6. **Stooq** daily CSV

Prints `PASS` / `FAIL` per provider with a one-line reason, and exits
non-zero if any of the three required providers (GDELT, USGS, Binance)
failed.

Usage:
    python scripts/verify_live_providers.py
    python scripts/verify_live_providers.py --all      # include 4-6
    python scripts/verify_live_providers.py --verbose  # show tracebacks
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import datetime, timedelta, timezone

# Make `src/` importable when run straight from a checkout.
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (_REPO_ROOT, os.path.join(_REPO_ROOT, "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from worldpulse.ingestion.markets import (  # noqa: E402
    BinancePublicMarketProvider,
    StooqMarketProvider,
)
from worldpulse.ingestion.providers.eonet import EONETProvider  # noqa: E402
from worldpulse.ingestion.providers.gdacs import GDACSProvider  # noqa: E402
from worldpulse.ingestion.providers.gdelt import GDELTProvider  # noqa: E402
from worldpulse.ingestion.providers.usgs import USGSProvider  # noqa: E402

NOW = datetime.now(timezone.utc)


# --- individual checks --------------------------------------------------

def check_gdelt() -> str:
    """GDELT DOC 2.0 article search over the last 24 hours."""
    provider = GDELTProvider(max_records=20)
    start = NOW - timedelta(hours=24)
    events = provider.fetch_events(start, NOW)
    if provider.health.error_count:
        raise RuntimeError(provider.health.last_error or "unknown GDELT error")
    if not events:
        # Reachable but empty is a soft signal, not a schema break: the
        # keyword sets may genuinely have no hits in a 24h window.
        return "reachable, but 0 articles matched the domain keyword sets in the last 24h"
    sample = events[0]
    return (f"{len(events)} events; newest '{sample.headline[:60]}...' "
            f"from {sample.source_name} at {sample.occurred_at.isoformat()}")


def check_usgs() -> str:
    """USGS FDSN historical query AND the live summary feed."""
    provider = USGSProvider(min_magnitude=4.0)

    # 1. Historical range (this is the endpoint backfill depends on).
    hist_end = NOW - timedelta(days=30)
    hist_start = hist_end - timedelta(days=7)
    historical = provider.fetch_events(hist_start, hist_end)
    if provider.health.error_count:
        raise RuntimeError(provider.health.last_error or "unknown USGS FDSN error")
    if not historical:
        raise RuntimeError(
            f"FDSN query returned no M4.0+ events for {hist_start.date()}..{hist_end.date()}, "
            "which is implausible -- schema or parameters may have changed"
        )

    # 2. Live summary feed (the cheap polling path).
    live_features = provider._fetch_summary_feed()

    sample = historical[0]
    return (f"FDSN: {len(historical)} M4.0+ events in a 7-day window 30 days back "
            f"(e.g. M{sample.raw_payload['properties'].get('mag')} {sample.locations}); "
            f"summary feed: {len(live_features)} features in the last hour")


def check_binance() -> str:
    """Binance public klines -- the free, keyless market data path."""
    provider = BinancePublicMarketProvider()
    end = NOW
    start = end - timedelta(hours=6)
    bars = provider.get_bars("BTC-USD", start, end, interval="1h")
    if not bars:
        raise RuntimeError("no klines returned for BTCUSDT over the last 6 hours")
    latest = bars[-1]
    if latest.close <= 0:
        raise RuntimeError(f"implausible close price {latest.close}")
    return (f"{len(bars)} hourly BTCUSDT klines; latest close {latest.close} "
            f"at {latest.timestamp.isoformat()}")


def check_eonet() -> str:
    provider = EONETProvider(status="all")
    events = provider.fetch_events(NOW - timedelta(days=30), NOW)
    if provider.health.error_count:
        raise RuntimeError(provider.health.last_error or "unknown EONET error")
    if not events:
        return "reachable, but 0 events in the last 30 days"
    subtypes = sorted({e.event_subtype for e in events})
    return f"{len(events)} events; subtypes {subtypes[:6]}"


def check_gdacs() -> str:
    provider = GDACSProvider()
    events = provider.fetch_events(NOW - timedelta(days=14), NOW)
    if provider.health.error_count:
        raise RuntimeError(provider.health.last_error or "unknown GDACS error")
    if not events:
        return "reachable, but 0 alerts in the last 14 days"
    levels = sorted({e.event_subtype_detail for e in events})
    return f"{len(events)} alerts; hazard/alert codes {levels[:6]}"


def check_stooq() -> str:
    provider = StooqMarketProvider()
    bars = provider.get_bars("^GSPC", NOW - timedelta(days=30), NOW, interval="1d")
    if not bars:
        raise RuntimeError("no daily bars returned for ^spx")
    return f"{len(bars)} daily ^SPX bars; latest close {bars[-1].close} on {bars[-1].timestamp.date()}"


REQUIRED = [
    ("GDELT DOC 2.0", check_gdelt),
    ("USGS (FDSN + summary feed)", check_usgs),
    ("Binance public klines", check_binance),
]

OPTIONAL = [
    ("NASA EONET v3", check_eonet),
    ("GDACS EVENTS4APP", check_gdacs),
    ("Stooq daily CSV", check_stooq),
]


def run(checks, verbose: bool) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    for name, fn in checks:
        print(f"--- {name} ...", flush=True)
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - this script reports, never crashes
            detail = f"{type(exc).__name__}: {exc}"
            if verbose:
                traceback.print_exc()
            results.append((name, False, detail))
            print(f"    FAIL  {detail}\n", flush=True)
        else:
            results.append((name, True, detail))
            print(f"    PASS  {detail}\n", flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true",
                        help="also check EONET, GDACS and Stooq")
    parser.add_argument("--verbose", action="store_true", help="print tracebacks")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.ERROR,
        format="%(levelname)s %(name)s: %(message)s",
    )

    print("WorldPulse live provider verification")
    print(f"UTC now: {NOW.isoformat()}")
    print("These are REAL network calls. If they fail behind a proxy or in a")
    print("sandboxed environment, that is a network-reachability result, not a")
    print("code defect -- the offline parsing tests are in tests/.\n")

    required_results = run(REQUIRED, args.verbose)
    optional_results = run(OPTIONAL, args.verbose) if args.all else []

    print("=" * 68)
    print("SUMMARY")
    for name, ok, detail in required_results + optional_results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("=" * 68)

    failed = [name for name, ok, _ in required_results if not ok]
    if failed:
        print(f"\n{len(failed)} required provider(s) FAILED: {', '.join(failed)}")
        print("Check outbound network access / proxy allowlist, then re-run.")
        return 1
    print("\nAll required providers PASSED. WorldPulse can run in zero-cost mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
