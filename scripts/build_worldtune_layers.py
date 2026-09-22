#!/usr/bin/env python3
"""Build the bounded WorldTune Silver and Gold layers from a GDELT extract.

This is intentionally local and deterministic.  It does not claim that GKG
metadata is article text, and it does not introduce a database or an LLM.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/gdelt/gdelt_gkg_20260904_20260919.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/layers"

TOPICS = {
    "crypto": r"bitcoin|crypto|ethereum|blockchain|web3|defi|stablecoin|binance|coinbase|solana|dogecoin|nft",
    "technology": r"artificial intelligence|technology|software|semiconductor|chip|cybersecurity|robotics|quantum|cloud computing",
    "macro_policy": r"federal reserve|fed |interest rate|repo rate|inflation|rbi|central bank|monetary policy|tariff",
    "india": r"india|rbi|inr|bengaluru|bangalore|hindalco",
    "metals": r"gold|silver|aluminium|aluminum|copper|hindalco|metals",
    "geopolitics": r"\bwar\b|armed conflict|military|airstrike|air strike|missile|invasion|troops|ceasefire|sanction|embargo|diplomatic crisis|geopolitic|naval|drone attack|trade route|shipping disruption",
}

# A transparent prior, not a claim about publisher reliability.
QUALITY = {"reuters.com": 1.0, "apnews.com": 1.0, "bbc.com": 0.95, "ft.com": 0.95}


def _text(frame: pd.DataFrame) -> pd.Series:
    cols = [c for c in ("url", "title", "themes", "organizations", "locations", "persons") if c in frame]
    result = frame[cols[0]].fillna("").astype(str) if cols else pd.Series("", index=frame.index)
    for col in cols[1:]:
        result = result + " " + frame[col].fillna("").astype(str)
    return result.str.lower()


def build(source: Path, out: Path) -> dict:
    frame = pd.read_parquet(source)
    required = {"published_at", "url", "domain"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"GDELT extract missing required columns: {sorted(missing)}")
    frame["published_at"] = pd.to_datetime(frame["published_at"], utc=True, errors="coerce")
    frame = frame[frame["published_at"].notna()].copy()
    frame["normalized_url"] = frame["normalized_url"].fillna(frame["url"]).astype(str).str.strip().str.lower()
    frame = frame[frame["normalized_url"] != ""].drop_duplicates("normalized_url", keep="first")
    frame["date"] = frame["published_at"].dt.date.astype(str)
    frame["source"] = "gdelt_gkg"
    frame["source_quality"] = frame["domain"].fillna("").map(lambda d: QUALITY.get(str(d).lower(), 0.5))
    text = _text(frame)
    for name, pattern in TOPICS.items():
        frame[f"topic_{name}"] = text.str.contains(pattern, regex=True, na=False)

    silver_cols = ["published_at", "date", "source", "url", "normalized_url", "domain", "source_country", "language", "title", "themes", "locations", "persons", "organizations", "tone", "source_file", "source_quality"]
    silver_cols += [f"topic_{name}" for name in TOPICS]
    for col in silver_cols:
        if col not in frame:
            frame[col] = ""
    out.mkdir(parents=True, exist_ok=True)
    silver = out / "silver_articles.parquet"
    frame[silver_cols].to_parquet(silver, index=False)

    topic_rows = []
    for date, group in frame.groupby("date", sort=True):
        row = {"date": date, "articles": int(len(group)), "mean_source_quality": round(float(group.source_quality.mean()), 6)}
        row.update({f"{name}_articles": int(group[f"topic_{name}"].sum()) for name in TOPICS})
        topic_rows.append(row)
    daily = pd.DataFrame(topic_rows)
    daily.to_parquet(out / "gold_daily_topic_metrics.parquet", index=False)

    domains = (frame.groupby(["date", "domain"], dropna=False).agg(
        articles=("normalized_url", "size"), mean_source_quality=("source_quality", "mean")
    ).reset_index().sort_values(["date", "articles"], ascending=[True, False]))
    domains.to_parquet(out / "gold_source_metrics.parquet", index=False)

    entities = []
    for name in TOPICS:
        subset = frame[frame[f"topic_{name}"]]
        entities.extend({"date": d, "entity": name, "articles": int(len(g)), "source": "gdelt_gkg"} for d, g in subset.groupby("date"))
    pd.DataFrame(entities, columns=["date", "entity", "articles", "source"]).to_parquet(out / "gold_daily_entity_metrics.parquet", index=False)
    manifest = {
        "source": str(source.resolve()), "source_type": "gdelt_gkg", "silver": str(silver),
        "dedup_key": "normalized_url", "input_rows": int(len(pd.read_parquet(source, columns=["url"]))),
        "silver_rows": int(len(frame)), "window_utc": [frame.published_at.min().isoformat(), frame.published_at.max().isoformat()],
        "topics": list(TOPICS), "quality_prior": QUALITY,
        "limitations": ["GKG metadata is not article text", "topic matches are recall-oriented", "source_quality is an explicit prior, not verification"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
