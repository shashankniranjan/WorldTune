"""Adapters for the evidence-backed local World Shift artifact."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PATH = ROOT / "data/processed/worldtune/world_shifts/gold_world_shifts.parquet"


def _list(value: object) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def _value(value: object) -> object:
    try:
        return json.loads(value or "null")
    except (TypeError, ValueError):
        return value


def _row(row: dict) -> dict:
    evidence = {
        "article_count": int(row["evidence_article_count"]),
        "unique_domain_count": int(row["evidence_unique_domains"]),
        "zscore": float(row["evidence_zscore"]),
        "volume_growth_1d": float(row["evidence_volume_growth_1d"]),
    }
    return {
        "shift_id": row["shift_id"], "date": str(row["date"]), "category": row["category"],
        "topic": row["topic"], "direction": row["direction"], "direction_label": row["direction_label"],
        "summary": row["summary"], "status": row["status"], "scope": row["scope"],
        "organizations": _list(row["organizations"]), "locations": _list(row["locations"]),
        "related_topics": _list(row["related_topics"]), "representative_evidence": _list(row["representative_evidence"]),
        "signal_strength": float(row["signal_strength"]),
        "world_impact_score": float(row.get("world_impact_score", 0.0)),
        "persona_impact_score": float(row.get("persona_impact_score", 0.0)),
        "impact_gravity_score": float(row.get("impact_gravity_score", 0.0)),
        "priority_score": float(row.get("priority_score", row["signal_strength"])), "evidence": evidence,
        "provenance": _list(row["provenance"]), "tech_impact": _value(row["tech_impact"]),
        "finance_impact": _value(row["finance_impact"]),
    }


def load_shifts() -> list[dict]:
    path = Path(os.environ.get("WORLD_TUNE_SHIFTS_PATH", str(DEFAULT_PATH)))
    if not path.exists():
        return []
    frame = pd.read_parquet(path)
    rank_column = "priority_score" if "priority_score" in frame else "signal_strength"
    frame = frame.sort_values(["date", rank_column], ascending=[False, False])
    return [_row(r) for r in frame.to_dict("records")]


def list_shifts(limit: int = 20) -> list[dict]:
    shifts = load_shifts()
    if not shifts:
        return []
    latest = shifts[0]["date"]
    return [s for s in shifts if s["date"] == latest][:limit]


def get_shift(shift_id: str) -> dict | None:
    return next((s for s in load_shifts() if s["shift_id"] == shift_id), None)
