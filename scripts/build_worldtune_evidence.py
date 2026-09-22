#!/usr/bin/env python3
"""Build the explainable WorldTune Signal Evidence layer.

The input candidate and source records are both local, deterministic artifacts.
No LLM, embedding model, or external source is used here.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "data/processed/worldtune/signals/gold_signal_candidates.parquet"
DEFAULT_ARTICLES = ROOT / "data/processed/worldtune/layers/silver_articles.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/evidence"
WEIGHTS = {"anomaly": 0.40, "volume_growth": 0.25, "persistence": 0.20, "source_diversity": 0.15}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _tokens(series: pd.Series, limit: int = 20) -> list[str]:
    counts: dict[str, int] = {}
    for raw in series.fillna("").astype(str):
        for token in raw.split(";"):
            token = token.strip()
            if not token:
                continue
            # GKG entity fields use prefixes such as "1#Name#...".
            if "#" in token:
                pieces = token.split("#")
                token = pieces[1].strip() if len(pieces) > 1 and pieces[1].strip() else pieces[0].strip()
            counts[token] = counts.get(token, 0) + 1
    return [name for name, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]]


def _top_domains(frame: pd.DataFrame, limit: int = 20) -> list[str]:
    return frame["domain"].fillna("").astype(str).loc[lambda s: s != ""].value_counts().head(limit).index.tolist()


def _representative(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, str]]:
    """Prefer one record per domain, then fill by unseen normalized URL."""
    work = frame.copy()
    work["domain"] = work["domain"].fillna("").astype(str)
    work = work.sort_values(["source_quality", "domain", "url"], ascending=[False, True, True])
    selected: list[dict[str, str]] = []
    domains: set[str] = set()
    urls: set[str] = set()
    for prefer_unique_domain in (True, False):
        for row in work.itertuples(index=False):
            url = str(getattr(row, "url", "") or "")
            domain = str(getattr(row, "domain", "") or "")
            if not url or url in urls or (prefer_unique_domain and domain in domains):
                continue
            selected.append({"title": str(getattr(row, "title", "") or ""), "url": url, "domain": domain})
            urls.add(url); domains.add(domain)
            if len(selected) >= limit:
                return selected
    return selected


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 6)


def build(candidates_path: Path, articles_path: Path, out: Path) -> dict:
    candidates = pd.read_parquet(candidates_path)
    candidates["date"] = pd.to_datetime(candidates["date"], utc=True)
    candidates = candidates[candidates["eligible"] == True].copy()  # noqa: E712
    articles = pd.read_parquet(articles_path)
    articles["date"] = pd.to_datetime(articles["date"], utc=True)
    articles["domain"] = articles["domain"].fillna("").astype(str)
    articles["source_quality"] = pd.to_numeric(articles.get("source_quality", 0.5), errors="coerce").fillna(0.5)

    rows: list[dict] = []
    missing = 0
    for candidate in candidates.itertuples(index=False):
        entity = candidate.entity
        date = candidate.date
        mask = articles["date"].eq(date)
        if entity != "all":
            flag = f"topic_{entity}"
            mask &= articles[flag].eq(True) if flag in articles else False
        evidence = articles.loc[mask].copy()
        if evidence.empty:
            missing += 1

        # The source diversity metric is normalized Shannon entropy: 1 means
        # evenly distributed across domains; 0 means one domain only.
        domain_counts = evidence["domain"].value_counts()
        unique_domains = int(domain_counts.size)
        if unique_domains > 1:
            proportions = domain_counts / domain_counts.sum()
            diversity = float(-(proportions * proportions.map(math.log)).sum() / math.log(unique_domains))
        else:
            diversity = 0.0

        z = float(candidate.prior_7d_zscore)
        growth_1d = float(candidate.day_change) if pd.notna(candidate.day_change) else 0.0
        # Scores are bounded and documented V1 transformations.
        anomaly_score = _clip(abs(z) / 4.0)
        growth_score = _clip(abs(growth_1d) / 1.0)

        history = candidates[(candidates.entity == entity) & (candidates.date <= date)].sort_values("date")
        abnormal = history[history["prior_7d_zscore"].abs() >= 2.0]
        consecutive = 0
        for value in reversed(history["prior_7d_zscore"].tolist()):
            if abs(float(value)) >= 2.0:
                consecutive += 1
            else:
                break
        recent_3 = history.tail(3)
        recent_7 = history.tail(7)
        anomaly_3 = float(recent_3["prior_7d_zscore"].abs().mean()) if len(recent_3) else 0.0
        anomaly_7 = float(recent_7["prior_7d_zscore"].abs().mean()) if len(recent_7) else 0.0
        peak_z = float(history["prior_7d_zscore"].abs().max()) if len(history) else 0.0
        values = history["value"].tolist()
        growth_3 = (values[-1] / values[-4] - 1.0) if len(values) >= 4 and values[-4] else 0.0
        growth_7 = (values[-1] / values[-8] - 1.0) if len(values) >= 8 and values[-8] else 0.0
        acceleration = growth_1d - (float(history["day_change"].iloc[-2]) if len(history) >= 2 and pd.notna(history["day_change"].iloc[-2]) else 0.0)
        persistence_score = _clip(0.5 * min(consecutive / 4.0, 1.0) + 0.5 * min(len(abnormal.tail(7)) / 4.0, 1.0))
        signal_strength = round(WEIGHTS["anomaly"] * anomaly_score + WEIGHTS["volume_growth"] * growth_score + WEIGHTS["persistence"] * persistence_score + WEIGHTS["source_diversity"] * _clip(diversity), 6)
        rows.append({
            "date": date, "entity": entity, "source": "gdelt_gkg", "article_count": int(len(evidence)),
            "prior_7d_mean": float(candidate.prior_7d_mean), "volume_ratio": (float(candidate.value) / float(candidate.prior_7d_mean) if candidate.prior_7d_mean else None),
            "zscore": z, "consecutive_abnormal_days": consecutive, "days_above_baseline_3d": int((recent_3["prior_7d_zscore"].abs() >= 2).sum()),
            "days_above_baseline_7d": int((recent_7["prior_7d_zscore"].abs() >= 2).sum()), "anomaly_3d": anomaly_3, "anomaly_7d": anomaly_7,
            "peak_zscore": peak_z, "volume_growth_1d": growth_1d, "volume_growth_3d": growth_3, "volume_growth_7d": growth_7, "acceleration": acceleration,
            "unique_domain_count": unique_domains, "domain_diversity": round(diversity, 6),
            "top_themes": _json(_tokens(evidence["themes"])), "top_organizations": _json(_tokens(evidence["organizations"])),
            "top_people": _json(_tokens(evidence["persons"])), "top_locations": _json(_tokens(evidence["locations"])),
            "top_domains": _json(_top_domains(evidence)), "representative_articles": _json(_representative(evidence)),
            "anomaly_score": anomaly_score, "volume_growth_score": growth_score, "persistence_score": persistence_score,
            "source_diversity_score": _clip(diversity), "signal_strength": signal_strength,
        })

    evidence = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    evidence.to_parquet(out / "gold_signal_evidence.parquet", index=False)
    strongest = evidence.nlargest(10, "signal_strength")[["date", "entity", "signal_strength", "zscore", "article_count"]].to_dict("records")
    weakest = evidence.nsmallest(10, "signal_strength")[["date", "entity", "signal_strength", "zscore", "article_count"]].to_dict("records")
    summary = {
        "input_candidate_rows": int(len(pd.read_parquet(candidates_path))), "eligible_candidates": int(len(candidates)),
        "generated_evidence_rows": int(len(evidence)), "missing_evidence_count": missing,
        "strongest_signals": strongest, "weakest_signals": weakest,
        "representative_examples": evidence.head(3)[["date", "entity", "representative_articles"]].to_dict("records"),
        "weights": WEIGHTS,
        "score_definitions": {"anomaly_score": "clip(abs(zscore)/4, 0, 1)", "volume_growth_score": "clip(abs(volume_growth_1d), 0, 1)", "persistence_score": "0.5*clip(consecutive_abnormal_days/4)+0.5*clip(abnormal_days_7d/4)", "source_diversity_score": "normalized Shannon entropy over domains", "signal_strength": "weighted sum of the four component scores"},
        "limitations": ["GDELT GKG metadata is not article text", "candidate categories are broad keyword flags", "one GDELT source cannot establish cross-source confirmation", "association is not causation", "representative titles may be empty in this extract"],
    }
    (out / "validation_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (out / "manifest.json").write_text(json.dumps({"input_candidates": str(candidates_path.resolve()), "input_articles": str(articles_path.resolve()), "output": str((out / 'gold_signal_evidence.parquet').resolve()), "summary": str((out / 'validation_summary.json').resolve())}, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.candidates, args.articles, args.out), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
