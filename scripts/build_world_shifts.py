#!/usr/bin/env python3
"""Discover evidence-backed, user-facing World Shifts from GDELT evidence.

Subtopics are emitted only when their transparent vocabulary matches source
records.  The vocabulary is a discovery detector, not a claim that every
matching article is about the named concept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "data/processed/worldtune/evidence/gold_signal_evidence.parquet"
DEFAULT_ARTICLES = ROOT / "data/processed/worldtune/layers/silver_articles.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/world_shifts"

DETECTORS = {
    "technology": {
        "AI Infrastructure": r"artificial intelligence|machine learning|\bai\b|gpu|nvidia|openai|inference|cuda|data cent(?:er|re)|cloud computing",
        "Semiconductors": r"\bsemiconductor\w*\b|chip fabrication|\bfoundry\b|\bnvidia\b|\bamd\b|\btsmc\b|\bintel\b",
        "Cloud Infrastructure": r"cloud computing|cloud infrastructure|data cent(?:er|re)|aws|azure|google cloud",
        "Cybersecurity": r"cybersecurity|cyber security|ransomware|malware|data breach|zero.?trust",
        "Quantum Computing": r"quantum computing|quantum computer|qubit",
    },
    # Require both a digital-asset term and a regulatory/policy term.  The
    # previous `regulator|sec` alternatives pulled unrelated crypto-adjacent
    # stories (and even non-crypto policy coverage) into this shift.
    "crypto": {"Crypto Regulation": r"(?=.*(?:\bcrypto\b|\bcryptocurrency\b|digital asset|\bstablecoin\b|\bblockchain\b|\bdefi\b|\btoken\w*|\bbitcoin\b|\bethereum\b))(?=.*(?:\bregulat\w*|\bsec\b|\bsecurities\b|\bcommission\b|\bpolicy\b|\bcompliance\b|\blegislat\w*|\blaw\b|\bban\b|\boversight\b))"},
    "macro_policy": {"Inflation and Rates": r"inflation|interest rate|federal reserve|central bank|monetary policy|repo rate"},
    "metals": {"Gold and Safe Havens": r"gold (?:price|market|bullion|futures|mining|miner|investment|bar|reserve)|golden? bullion|safe haven|precious metal|silver (?:price|market|bullion|futures|mining|miner|investment)|bullion"},
    "india": {"India Digital Policy": r"(?=.*(?:india|indian|rbi|upi))(?=.*(?:digital|data protection|privacy|public infrastructure|fintech|payment|policy|regulat))"},
    "geopolitics": {
        "Armed Conflict and Military Escalation": r"\bwar\b|armed conflict|military (?:attack|strike|operation|escalation)|air ?strike|missile (?:attack|strike|launch)|invasion|troop deployment|drone attack|naval attack",
        "Sanctions and Economic Warfare": r"sanction|embargo|asset freeze|export control|economic warfare|trade restriction",
        "Energy and Trade Route Disruption": r"shipping disruption|trade route|strait of hormuz|red sea|suez canal|oil supply disruption|gas supply disruption|port blockade",
        "Diplomatic Crisis": r"diplomatic crisis|expel(?:led|s)? diplomat|break off relations|recall(?:ed|s)? ambassador|ceasefire talks|peace talks",
    },
}

# These are explicit product-policy priors, not facts inferred from GDELT.  The
# persona is the seeded WorldTune profile: India-based data/AI engineer working
# with European technology, active in crypto, with gold/silver/HINDALCO context.
IMPACT_PRIORS = {
    "AI Infrastructure": (0.65, 0.95), "Semiconductors": (0.75, 0.90),
    "Cloud Infrastructure": (0.60, 0.90), "Cybersecurity": (0.80, 0.90),
    "Quantum Computing": (0.55, 0.75), "Crypto Regulation": (0.65, 1.00),
    "Inflation and Rates": (0.85, 0.90), "Gold and Safe Havens": (0.60, 0.90),
    "India Digital Policy": (0.65, 1.00),
    "Armed Conflict and Military Escalation": (1.00, 0.85),
    "Sanctions and Economic Warfare": (0.90, 0.85),
    "Energy and Trade Route Disruption": (0.90, 0.90),
    "Diplomatic Crisis": (0.75, 0.65),
}
GRAVITY_WEIGHTS = {"world": 0.60, "persona": 0.40}
PRIORITY_WEIGHTS = {"gravity": 0.50, "attention": 0.35, "evidence_quality": 0.15}
MIN_PRIORITY = 0.35

# The five topics with hand-written editorial context in
# app/services/world_shift_contract.py::_editorial_context. Everything else
# uses the generic fallback there, so "trending" is deliberately scoped to
# topics OUTSIDE this set -- it exists to surface what's spiking right now
# even when nobody has written bespoke prose for it yet.
EDITORIAL_TOPIC_MARKERS = ("armed conflict", "inflation", "ai infrastructure", "semiconductor", "cyber")
TRENDING_SLOTS = 3
# A trending pick must be a genuine spike, not noise: at least this many
# articles and this many distinct domains on the day, so a single syndicated
# story (or a slow news day inflating a z-score off a near-zero baseline)
# can't buy a "Trending" badge.
TRENDING_MIN_ARTICLES = 5
TRENDING_MIN_DOMAINS = 3


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _parse(value: object) -> list:
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except (TypeError, ValueError):
        return []


def _direction(z: float) -> tuple[str, str]:
    if z >= 2:
        return "up", "SURGING"
    if z >= 0.75:
        return "up", "RISING"
    if z <= -2:
        return "down", "COOLING"
    if z <= -0.75:
        return "down", "FALLING"
    return "flat", "STABLE"


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 6)


def _topic_history(articles: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    """Calculate named-topic metrics causally across all observed dates."""
    dates = pd.Index(sorted(articles["date"].dropna().unique()))
    counts = matched.groupby("date").size().reindex(dates, fill_value=0).astype(float)
    domains = matched.groupby("date")["domain"].nunique().reindex(dates, fill_value=0).astype(float)
    prior_mean = counts.shift(1).rolling(7, min_periods=3).mean()
    prior_std = counts.shift(1).rolling(7, min_periods=3).std(ddof=0)
    zscore = ((counts - prior_mean) / prior_std.where(prior_std > 0)).fillna(0.0)
    growth = counts.pct_change(fill_method=None).replace([math.inf, -math.inf], 0.0).fillna(0.0)
    abnormal = zscore.abs().ge(2.0)
    consecutive: list[int] = []
    run = 0
    for value in abnormal:
        run = run + 1 if value else 0
        consecutive.append(run)
    return pd.DataFrame({"count": counts, "domains": domains, "zscore": zscore,
                         "growth": growth, "abnormal": abnormal,
                         "consecutive": consecutive}, index=dates)


def _scores(topic: str, history: pd.DataFrame, date: object, diversity: float) -> dict[str, float]:
    current = history.loc[date]
    recent = history.loc[:date].tail(7)
    anomaly = _clip(abs(float(current.zscore)) / 4.0)
    growth = _clip(abs(float(current.growth)))
    persistence = _clip(0.5 * min(float(current.consecutive) / 4.0, 1.0)
                        + 0.5 * min(float(recent.abnormal.sum()) / 4.0, 1.0))
    attention = _clip(0.40 * anomaly + 0.25 * growth + 0.20 * persistence + 0.15 * diversity)
    breadth = _clip(math.log1p(float(current.domains)) / math.log1p(250.0))
    world_prior, persona = IMPACT_PRIORS.get(topic, (0.50, 0.50))
    world = _clip(0.65 * world_prior + 0.20 * breadth + 0.15 * persistence)
    gravity = _clip(GRAVITY_WEIGHTS["world"] * world + GRAVITY_WEIGHTS["persona"] * persona)
    evidence_quality = _clip(0.60 * diversity + 0.40 * breadth)
    priority = _clip(PRIORITY_WEIGHTS["gravity"] * gravity
                     + PRIORITY_WEIGHTS["attention"] * attention
                     + PRIORITY_WEIGHTS["evidence_quality"] * evidence_quality)
    return {"anomaly_score": anomaly, "volume_growth_score": growth,
            "persistence_score": persistence, "source_diversity_score": _clip(diversity),
            "signal_strength": attention, "world_impact_score": world,
            "persona_impact_score": persona, "impact_gravity_score": gravity,
            "evidence_quality_score": evidence_quality, "priority_score": priority,
            "zscore": float(current.zscore), "growth_1d": float(current.growth),
            "consecutive": int(current.consecutive), "abnormal_7d": int(recent.abnormal.sum())}


def _shift_id(date: str, category: str, topic: str) -> str:
    key = f"{date}|{category}|{topic}".encode()
    return f"shift_{date.replace('-', '')}_{hashlib.sha1(key).hexdigest()[:10]}"


def build(evidence_path: Path, articles_path: Path, out: Path) -> dict:
    evidence = pd.read_parquet(evidence_path)
    evidence["date"] = pd.to_datetime(evidence["date"], utc=True)
    evidence = evidence[evidence.entity != "all"].copy()
    articles = pd.read_parquet(articles_path)
    articles["date"] = pd.to_datetime(articles["date"], utc=True)
    # Topic evidence is selected from publisher URL/title text only. GKG
    # themes, organizations and locations are useful facets, but using them
    # as detector text caused unrelated syndicated stories to match a shift.
    text_cols = [c for c in ["url", "title"] if c in articles]
    text = articles[text_cols[0]].fillna("").astype(str).str.lower()
    for col in text_cols[1:]:
        text = text + " " + articles[col].fillna("").astype(str).str.lower()
    articles["_search_text"] = text

    matched_by_topic: dict[tuple[str, str], pd.DataFrame] = {}
    for category, detectors in DETECTORS.items():
        flag = f"topic_{category}"
        category_articles = articles[articles[flag].eq(True)] if flag in articles else articles
        for topic, pattern in detectors.items():
            matched_by_topic[(category, topic)] = category_articles[
                category_articles["_search_text"].str.contains(pattern, regex=True, na=False)
            ]
    histories = {key: _topic_history(articles, matched) for key, matched in matched_by_topic.items()}

    shifts: list[dict] = []
    for row in evidence.itertuples(index=False):
        category = row.entity
        detectors = DETECTORS.get(category, {})
        for topic in detectors:
            match = matched_by_topic[(category, topic)]
            match = match[match.date == row.date]
            if len(match) < 3:
                continue
            domains = match.domain.fillna("").astype(str).replace("", pd.NA).dropna().nunique()
            domain_counts = match.domain.fillna("").astype(str).value_counts()
            if len(domain_counts) > 1:
                proportions = domain_counts / domain_counts.sum()
                diversity = float(-(proportions * proportions.map(math.log)).sum() / math.log(len(domain_counts)))
            else:
                diversity = 0.0
            scores = _scores(topic, histories[(category, topic)], row.date, diversity)
            if scores["priority_score"] < MIN_PRIORITY:
                continue
            direction, label = _direction(scores["zscore"])
            status = "persistent" if scores["consecutive"] >= 2 or scores["abnormal_7d"] >= 2 else "emerging"
            orgs = match.organizations.fillna("").astype(str).str.split(";").explode().str.extract(r"^[^#]*#?([^#;]+)")[0].dropna().value_counts().head(10).index.tolist()
            locations = match.locations.fillna("").astype(str).str.split(";").explode().str.extract(r"^[^#]*#?([^#,;]+)")[0].dropna().value_counts().head(10).index.tolist()
            representative = []
            for item in match.sort_values(["domain", "url"]).drop_duplicates("domain").head(10).itertuples(index=False):
                url = str(getattr(item, "url", "") or "")
                if url:
                    # GDELT GKG titles are frequently empty in this extract.
                    # Do not manufacture a headline from the domain; bounded
                    # enrichment may fill it later.
                    representative.append({"title": str(getattr(item, "title", "") or "").strip(), "url": url, "domain": str(getattr(item, "domain", "") or "")})
            date = row.date.date().isoformat()
            shifts.append({
                "shift_id": _shift_id(date, category, topic), "date": row.date, "category": category, "topic": topic,
                "direction": direction, "direction_label": label,
                "summary": f"{topic} attention is {label.lower()} across {max(1, domains)} observed domains.",
                "status": status, "scope": "global", "organizations": _json(orgs), "locations": _json(locations),
                "related_topics": _json([]), "representative_evidence": _json(representative),
                "signal_strength": scores["signal_strength"],
                "world_impact_score": scores["world_impact_score"],
                "persona_impact_score": scores["persona_impact_score"],
                "impact_gravity_score": scores["impact_gravity_score"],
                "evidence_quality_score": scores["evidence_quality_score"],
                "priority_score": scores["priority_score"],
                "anomaly_score": scores["anomaly_score"],
                "volume_growth_score": scores["volume_growth_score"],
                "persistence_score": scores["persistence_score"],
                "source_diversity_score": scores["source_diversity_score"],
                "evidence_article_count": int(len(match)), "evidence_unique_domains": int(domains),
                "evidence_zscore": scores["zscore"], "evidence_volume_growth_1d": scores["growth_1d"],
                "is_trending": False,  # set below, once every row for the date is known
                "provenance": _json([{"type": "OBSERVED", "text": "GDELT records matched the subtopic detector."}, {"type": "CALCULATED", "text": "Direction and strength are derived from the evidence layer."}, {"type": "INFERRED", "text": "The shift may matter to the relevant domain; no causal claim is made."}]),
                "tech_impact": _json({"status": "not_supported", "observed": [], "inferred": [], "reason": "GDELT-only evidence does not establish skills or career demand."}),
                "finance_impact": _json({"status": "not_supported", "observed": [], "inferred": [], "reason": "No market or company evidence is attached in this iteration."}),
            })

    frame = pd.DataFrame(shifts)
    if not frame.empty:
        # Same-day subtopics in one category are associations, never causality.
        for idx, item in frame.iterrows():
            peers = frame[(frame.date == item.date) & (frame.category == item.category) & (frame.shift_id != item.shift_id)].sort_values("priority_score", ascending=False).head(5).topic.tolist()
            frame.at[idx, "related_topics"] = _json([{"topic": p, "relationship": "associated_with"} for p in peers])
        # Trending: the top TRENDING_SLOTS topics per day by attention spike
        # (z-score), restricted to topics that don't already have hand-written
        # editorial context and that clear a minimum evidence bar. This reuses
        # the anomaly detection already computed in _topic_history/_scores --
        # no new vocabulary or entity extraction, just a different selection
        # over the same numbers.
        is_editorial = frame.topic.str.lower().apply(
            lambda topic: any(marker in topic for marker in EDITORIAL_TOPIC_MARKERS)
        )
        eligible = frame[
            ~is_editorial
            & (frame.evidence_article_count >= TRENDING_MIN_ARTICLES)
            & (frame.evidence_unique_domains >= TRENDING_MIN_DOMAINS)
        ]
        for _, day_rows in eligible.groupby("date"):
            top = day_rows.sort_values("evidence_zscore", ascending=False).head(TRENDING_SLOTS)
            frame.loc[top.index, "is_trending"] = True
    out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / "gold_world_shifts.parquet", index=False)
    frame.to_json(out / "world_state.json", orient="records", date_format="iso", indent=2)
    trending_topics = sorted(frame[frame.is_trending].topic.unique().tolist()) if len(frame) and "is_trending" in frame else []
    summary = {"generated_shifts": int(len(frame)), "categories": sorted(frame.category.unique().tolist()) if len(frame) else [], "topics": sorted(frame.topic.unique().tolist()) if len(frame) else [], "trending_topics": trending_topics, "excluded_broad_category": "all", "gravity_weights": GRAVITY_WEIGHTS, "priority_weights": PRIORITY_WEIGHTS, "minimum_priority": MIN_PRIORITY, "impact_priors": IMPACT_PRIORS, "persona_profile": "India-based data/AI engineer in European technology consulting; crypto participant; gold, silver and HINDALCO context", "limitations": ["impact priors are explicit product-policy judgements, not observed facts", "subtopics are vocabulary-based discovery candidates, not verified events", "GDELT-only evidence cannot confirm real-world activity or causal relationships", "empty source titles receive a non-empty UI-safe fallback", "trending topics are the top-3 non-editorial daily attention spikes by z-score, not independently verified as newsworthy"]}
    (out / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.evidence, args.articles, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
