#!/usr/bin/env python3
"""Build a bounded WorldTune personal-impact report from GDELT bulk data.

This is an evidence layer, not a trading signal: topic counts are descriptive
and market correlation is reported as insufficient unless aligned prices exist.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data/processed/gdelt/gdelt_gkg_20260904_20260919.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/impact_sample"

TOPICS = {
    "crypto": r"bitcoin|crypto|ethereum|blockchain|web3|defi|stablecoin|binance|coinbase|solana|dogecoin|nft",
    "technology": r"artificial intelligence|technology|software|semiconductor|chip|cybersecurity|robotics|quantum|cloud computing",
    "macro_policy": r"federal reserve|fed |interest rate|repo rate|inflation|rbi|central bank|monetary policy|tariff",
}

PERSONA = {
    "role": "Data engineer in European technology consulting",
    "location": "Bengaluru, India",
    "interests": ["crypto trading and investing", "data engineering", "AI", "European technology regulation"],
    "holdings": ["gold", "silver", "HINDALCO"],
}

HOLDING_IMPACT = {
    "gold": {"drivers": ["real yields", "USD", "inflation", "geopolitical risk"], "watch": ["Fed/RBI policy", "inflation", "safe-haven demand"]},
    "silver": {"drivers": ["industrial demand", "solar/electronics cycle", "USD", "real yields"], "watch": ["manufacturing", "technology capex", "commodity prices"]},
    "hindalco": {"drivers": ["aluminium/copper prices", "energy costs", "global manufacturing", "INR", "European demand"], "watch": ["metals prices", "EU industrial data", "China demand", "energy policy"]},
}

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default=str(DEFAULT_DATA)); ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    duckdb = shutil.which("duckdb")
    if not duckdb:
        raise SystemExit("duckdb CLI is required for bounded analysis; install duckdb or use the repository environment")
    source = str(Path(args.data).resolve()).replace("'", "''")
    def run(sql: str) -> list[dict]:
        raw = subprocess.check_output([duckdb, "-json", "-c", sql], text=True)
        return json.loads(raw or "[]")
    total = run(f"SELECT count(*) AS n FROM '{source}'")[0]["n"]
    daily = [(r["date"], r["n"]) for r in run(f"SELECT CAST(published_at AS DATE) AS date, count(*) AS n FROM '{source}' GROUP BY 1 ORDER BY 1")]
    topics = {}
    topic_daily = {}
    for name, pattern in TOPICS.items():
        p = pattern.replace("'", "''")
        fields = "lower(coalesce(url,'') || ' ' || coalesce(themes,'') || ' ' || coalesce(organizations,'') || ' ' || coalesce(locations,''))"
        where = f"regexp_matches({fields}, '{p}')"
        topics[name] = run(f"SELECT count(*) AS n FROM '{source}' WHERE {where}")[0]["n"]
        topic_daily[name] = [(r["date"], r["n"]) for r in run(f"SELECT CAST(published_at AS DATE) AS date, count(*) AS n FROM '{source}' WHERE {where} GROUP BY 1 ORDER BY 1")]

    # Existing smoke-test Binance files are intentionally checked for overlap.
    price_files = list((ROOT / "data_test/binance").glob("*_1h.json"))
    price_note = "No aligned crypto price series found."
    if price_files:
        price_note = "Only the existing smoke-test Binance files were found; they contain 10 hourly observations on 2026-09-19, insufficient for a 15-day correlation."

    report = {
        "persona": PERSONA,
        "window": {"start": str(daily[0][0]), "end": str(daily[-1][0]), "days_with_records": len(daily)},
        "dataset": {"path": str(Path(args.data).relative_to(ROOT)), "unique_records": total},
        "topic_counts": topics,
        "topic_share": {k: round(v / total, 6) for k, v in topics.items()},
        "daily_total_records": [{"date": str(d), "records": n} for d, n in daily],
        "daily_topic_counts": {k: [{"date": str(d), "records": n} for d, n in rows] for k, rows in topic_daily.items()},
        "market_alignment": {"status": "insufficient", "note": price_note, "required": "BTCUSDT/ETHUSDT hourly or daily prices covering the same window"},
        "holding_impact": {holding: {**HOLDING_IMPACT.get(holding.lower(), {"drivers": ["asset-specific news"], "watch": ["price and company filings"]}), "status": "context_only", "note": "No holding-level price or position-size data was supplied; this is a qualitative exposure map."} for holding in PERSONA["holdings"]},
        "impact_interpretation": {
            "crypto_trader_investor": ["Use crypto topic volume as an attention/risk-context feature; do not infer direction without price, volume, and event validation."],
            "european_tech_consultant": ["Use technology and macro-policy coverage to monitor client budget, regulation, cloud, AI, and data-governance risk."],
            "bengaluru_resident": ["Add India, RBI, INR, inflation, weather, infrastructure, and employment feeds before making local cost-of-living claims."],
        },
        "limitations": ["GDELT GKG has no reliable full article text in this extract.", "Keyword counts are recall-oriented and may include syndicated or irrelevant mentions.", "Source-country and language fields are empty in the current extract.", "This report is descriptive; it does not establish causality."],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    md = ["# WorldTune personal impact sample", "", f"Window: **{report['window']['start']} to {report['window']['end']}**", f"Persona: **{PERSONA['role']} in {PERSONA['location']}**", f"Holdings/watchlist: **{', '.join(PERSONA['holdings'])}**", "", "## Topic pulse", "", "| Topic | Records | Share |", "|---|---:|---:|"]
    md += [f"| {k} | {v:,} | {report['topic_share'][k]:.2%} |" for k, v in topics.items()]
    md += ["", "## Holding impact map", "", "| Holding | Main drivers | What WorldTune should monitor |", "|---|---|---|"]
    md += [f"| {h} | {', '.join(v['drivers'])} | {', '.join(v['watch'])} |" for h, v in report["holding_impact"].items()]
    md += ["", "## Interpretation", "", "- **Crypto:** topic volume is a market-attention feature, not a buy/sell signal.", "- **Work:** technology and macro-policy coverage can be mapped to EU regulation, AI, cloud, data governance, and consulting demand.", "- **Holdings:** gold, silver, and Hindalco receive separate impact explanations rather than being mixed into the crypto summary.", "- **Personal:** Bangalore and INR impact requires RBI, inflation, weather, employment, and FX series.", "", "## Correlation status", "", f"**Insufficient:** {price_note}", "", "## AI summary boundary", "", "The AI narrative layer should summarize only the deterministic topic counts, holding drivers, market observations, and cited evidence. It must not invent prices, positions, returns, or causal claims.", "", "## Limitations", ""]
    md += [f"- {x}" for x in report["limitations"]]
    (out / "report.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"report_json": str(out / 'report.json'), "report_markdown": str(out / 'report.md'), "topic_counts": topics, "market_correlation": "insufficient"}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
