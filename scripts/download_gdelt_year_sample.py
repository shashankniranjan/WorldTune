#!/usr/bin/env python3
"""Download one indexed GDELT GKG file per UTC day for a one-year baseline.

This is a disk-safe temporal sample, not a complete 15-minute-cadence archive.
The selection rule is deterministic: the indexed file nearest 12:00 UTC.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from test_gdelt_bulk import discover_gkg, fetch, norm_url, parse_file  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/gdelt_year_sample"
OUT = ROOT / "data/processed/gdelt"
log = logging.getLogger("gdelt_year_sample")


def choose_daily(files: list[tuple[datetime, str]]) -> list[tuple[datetime, str]]:
    by_day: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for item in files:
        by_day[item[0].date().isoformat()].append(item)
    selected = []
    for day, options in sorted(by_day.items()):
        target = datetime.fromisoformat(day).replace(hour=12, tzinfo=timezone.utc)
        selected.append(min(options, key=lambda item: abs((item[0] - target).total_seconds())))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--end", type=str, default="", help="UTC date YYYY-MM-DD; defaults to now")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    end = (datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) + timedelta(days=1)) if args.end else datetime.now(timezone.utc)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)
    RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    indexed = discover_gkg(start, end)
    selected = choose_daily(indexed)
    if len(selected) < args.days * 0.95:
        raise SystemExit(f"Only {len(selected)} daily files selected for {args.days}-day request")
    log.info("Year sample: %s -> %s; indexed=%d; selected=%d", start, end, len(indexed), len(selected))

    def download_one(item):
        stamp, url = item
        dest = RAW / url.rsplit("/", 1)[-1]
        if not fetch(url, dest):
            return None
        return dest, parse_file(dest)

    rows = []
    downloaded = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_one, item) for item in selected]
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result is None:
                continue
            dest, parsed = result; rows.extend(parsed); downloaded += 1
            if i % 25 == 0 or i == len(futures):
                log.info("[%d/%d] downloaded=%d records=%d", i, len(futures), downloaded, len(rows))

    frame = pd.DataFrame(rows)
    frame["published_at"] = pd.to_datetime(frame.timestamp, format="%Y%m%d%H%M%S", utc=True, errors="coerce")
    frame["normalized_url"] = frame.url.map(norm_url)
    frame = frame[frame.normalized_url != ""].drop_duplicates("normalized_url", keep="first")
    out = OUT / f"gdelt_gkg_year_sample_{start:%Y%m%d}_{(end - timedelta(seconds=1)):%Y%m%d}.parquet"
    frame.to_parquet(out, index=False)
    report = {
        "dataset": "GKG", "coverage_type": "one_indexed_file_per_utc_day", "selection_rule": "file nearest 12:00 UTC",
        "window_utc": [start.isoformat(), end.isoformat()], "indexed_files": len(indexed), "selected_daily_files": len(selected),
        "downloaded_files": downloaded, "raw_records": len(rows), "unique_articles": len(frame),
        "processed_path": str(out), "raw_path": str(RAW),
        "limitations": ["not a complete 15-minute cadence archive", "daily sample can miss intraday spikes", "GKG metadata is not article text"],
    }
    (OUT / "gdelt_year_sample_report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
