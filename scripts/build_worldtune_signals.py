#!/usr/bin/env python3
"""Derive causal, interpretable WorldTune signal candidates from Gold metrics.

Each row uses the current day's completed aggregate and prior rows only.  This
is a descriptive signal-candidate layer, not a trading recommendation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/worldtune/layers/gold_daily_topic_metrics.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/signals"


def build(source: Path, out: Path) -> dict:
    metrics = pd.read_parquet(source).sort_values("date").reset_index(drop=True)
    if metrics.empty or "date" not in metrics or "articles" not in metrics:
        raise ValueError("Gold topic metrics must contain date and articles")
    metrics["date"] = pd.to_datetime(metrics["date"], utc=True)
    topic_columns = [c for c in metrics.columns if c.endswith("_articles") and c != "articles"]

    rows = []
    for topic_col in ["articles", *topic_columns]:
        name = "all" if topic_col == "articles" else topic_col.removesuffix("_articles")
        values = pd.to_numeric(metrics[topic_col], errors="coerce").fillna(0.0)
        previous = values.shift(1)
        prior_mean = values.shift(1).rolling(7, min_periods=3).mean()
        prior_std = values.shift(1).rolling(7, min_periods=3).std(ddof=0)
        for i, date in enumerate(metrics["date"]):
            count = float(values.iloc[i])
            baseline = prior_mean.iloc[i]
            std = prior_std.iloc[i]
            z = (count - baseline) / std if pd.notna(std) and std > 0 else 0.0
            change = ((count / previous.iloc[i]) - 1.0) if previous.iloc[i] > 0 else None
            # A candidate is only emitted after enough prior observations exist.
            eligible = i >= 3
            if not eligible:
                label = "insufficient_history"
            elif z >= 2.0:
                label = "anomaly_high"
            elif z <= -2.0:
                label = "anomaly_low"
            elif pd.notna(change) and change > 0.10:
                label = "momentum_up"
            elif pd.notna(change) and change < -0.10:
                label = "momentum_down"
            else:
                label = "stable"
            rows.append({
                "date": date, "entity": name, "metric": "article_volume",
                "value": count, "prior_7d_mean": baseline if pd.notna(baseline) else None,
                "prior_7d_zscore": round(float(z), 6), "day_change": change,
                "signal": label, "eligible": eligible, "source": "gdelt_gkg",
            })

    signals = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    signals.to_parquet(out / "gold_signal_candidates.parquet", index=False)
    latest = signals[signals["date"] == signals["date"].max()].copy()
    latest.to_json(out / "latest_signal_candidates.json", orient="records", date_format="iso", indent=2)
    manifest = {
        "input": str(source.resolve()), "output": str((out / "gold_signal_candidates.parquet").resolve()),
        "rows": int(len(signals)), "entities": sorted(signals.entity.unique().tolist()),
        "causal_rule": "prior_7d_mean and prior_7d_zscore exclude the current day's value",
        "limitations": ["signals are news-volume candidates", "no price alignment or causal effect is established", "first three days are history-ineligible"],
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
