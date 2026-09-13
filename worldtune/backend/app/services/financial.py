"""Financial Pulse -- "what moved in the markets that matters to me, and why?"

Per asset, the pipeline is:

    price series  -> trend metrics        (app.analytics.trend)
    related news  -> intensity, sentiment (app.repositories / sentiment)
    both          -> trajectory           (app.analytics.trajectory)
    persona + all -> relevance            (app.ranking.relevance)
    everything    -> WorldTune score      (app.ranking.score)
    score+metrics -> explanation          (app.llm.explainer)

Ordering matters: the explanation is produced LAST, from values the
deterministic layers already computed. Nothing in the explanation path can
influence a number. That is the structural guarantee behind "the LLM never
invents a metric".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import trend as T
from app.analytics.trajectory import financial_trajectory
from app.llm.explainer import get_explainer
from app.models import MarketAssetORM, MarketPriceORM, NewsEventORM
from app.ranking.relevance import financial_relevance
from app.ranking.score import (
    compute_score,
    evidence_strength_score,
    novelty_score,
    prediction_confidence_score,
    recency_score,
    top_contributors,
    trend_momentum_score,
)
from app.schemas.persona import Persona

# News older than this does not inform a 7-day directional read.
NEWS_WINDOW_DAYS = 14
# Headline count that counts as "saturated" coverage when normalizing intensity.
INTENSITY_SATURATION = 8.0


def _price_rows(session: Session, symbol: str) -> list[MarketPriceORM]:
    return list(session.scalars(
        select(MarketPriceORM)
        .where(MarketPriceORM.asset_id == symbol)
        .order_by(MarketPriceORM.timestamp)
    ))


def _related_news(session: Session, symbol: str, sector: str, *,
                  as_of: datetime) -> list[NewsEventORM]:
    """News whose resolved tickers contain the symbol, or whose sectors match.

    The ticker/sector lists are JSON columns, so this filters in Python after
    a time-bounded fetch rather than with a JSON operator -- portable across
    SQLite and Postgres, and the window keeps the scan small.
    """
    since = as_of - timedelta(days=NEWS_WINDOW_DAYS)
    rows = session.scalars(
        select(NewsEventORM)
        .where(NewsEventORM.published_at >= since)
        .order_by(NewsEventORM.published_at.desc())
    ).all()
    out = []
    for row in rows:
        tickers = {t.upper() for t in (row.tickers or [])}
        sectors = {s.lower() for s in (row.sectors or [])}
        if symbol.upper() in tickers or (sector and sector.lower() in sectors):
            out.append(row)
    return out


def asset_pulse(session: Session, persona: Persona, asset: MarketAssetORM, *,
                as_of: datetime | None = None) -> dict | None:
    """The full explained entry for one asset, or None without enough data."""
    as_of = as_of or datetime.now(timezone.utc)
    rows = _price_rows(session, asset.id)
    if len(rows) < 10:
        return None

    closes = [r.close for r in rows]
    volumes = [r.volume for r in rows]
    price_trend = T.compute_trend(closes)
    news = _related_news(session, asset.id, asset.sector, as_of=as_of)

    news_count = len(news)
    news_intensity = min(1.0, news_count / INTENSITY_SATURATION)
    news_sentiment = (sum(n.sentiment for n in news) / news_count) if news_count else 0.0
    n_sources = len({n.source for n in news}) + 1  # +1: the price series itself

    trajectory = financial_trajectory(
        closes, volumes,
        news_sentiment=news_sentiment,
        news_intensity=news_intensity,
        horizon_days=7,
    )
    relevance = financial_relevance(
        persona,
        symbol=asset.id,
        asset_class=asset.asset_class,
        sector=asset.sector,
        signal_text=" ".join(n.title for n in news[:5]),
        entities=[e for n in news[:5] for e in (n.entities or [])],
    )

    change_24h = T.pct_change_over(closes, 1)
    volume_z = T.zscore(volumes, 30)
    latest_ts = rows[-1].timestamp
    most_recent_news = news[0].published_at if news else latest_ts

    evidence = [
        {"type": "price", "source": rows[-1].source,
         "detail": f"{asset.id} closed at {closes[-1]:,.2f} ({change_24h:+.2%} on the day)",
         "observed_at": latest_ts.isoformat()},
        {"type": "trend", "source": "worldtune:trend",
         "detail": (f"7d {price_trend.change_7d:+.2%}, 30d {price_trend.change_30d:+.2%}, "
                    f"volume z-score {volume_z:+.2f}"),
         "observed_at": latest_ts.isoformat()},
    ] + [
        {"type": "news", "source": n.source, "detail": n.title,
         "url": n.url, "observed_at": n.published_at.isoformat(),
         "sentiment": round(n.sentiment, 3)}
        for n in news[:3]
    ]

    breakdown = compute_score(
        persona_relevance=relevance.score,
        trend_momentum=trend_momentum_score(price_trend.change_7d,
                                            price_trend.acceleration / max(1.0, abs(closes[-1])),
                                            price_trend.zscore),
        evidence_strength=evidence_strength_score(
            n_sources=n_sources, n_observations=len(rows), corroborating_signals=news_count),
        novelty=novelty_score(zscore=price_trend.zscore, seen_before_count=0),
        # Recency of the freshest input (news if any, else the last bar).
        recency=recency_score(max(latest_ts, most_recent_news), as_of=as_of),
        prediction_confidence=prediction_confidence_score(trajectory.confidence,
                                                          trajectory.probability),
        relevance_components=relevance.components,
        evidence=evidence,
        reasons=relevance.reasons,
    )

    metrics = {
        "price": round(closes[-1], 4),
        "change_24h": round(change_24h, 6),
        "change_7d": round(price_trend.change_7d, 6),
        "change_30d": round(price_trend.change_30d, 6),
        "momentum": round(T.ewma_momentum(closes), 6),
        "acceleration": round(price_trend.acceleration, 6),
        "volume_zscore": round(volume_z, 4),
        "realized_volatility": round(T.realized_volatility(closes), 4),
        "news_count": news_count,
        "news_sentiment": round(news_sentiment, 4),
        "news_intensity": round(news_intensity, 4),
        "direction": trajectory.direction,
        "probability": trajectory.probability,
        "confidence": trajectory.confidence,
        "horizon_days": trajectory.horizon_days,
        "n_price_observations": len(rows),
    }

    explanation = get_explainer().explain(
        persona={"watchlist": persona.financial.watchlist,
                 "sectors": persona.financial.sectors,
                 "skills": persona.career.skills,
                 "target_roles": persona.career.target_roles,
                 "city": persona.location.city},
        signal={"domain": "financial", "label": asset.name or asset.id,
                "entity_id": asset.id, "sector": asset.sector,
                "asset_class": asset.asset_class},
        metrics=metrics,
        evidence=evidence,
        score=breakdown.to_dict(),
    )

    return {
        "entity_type": "asset",
        "entity_id": asset.id,
        "label": asset.name or asset.id,
        "asset_class": asset.asset_class,
        "sector": asset.sector,
        "worldtune_score": breakdown.score,
        "score_breakdown": breakdown.to_dict(),
        "top_contributors": top_contributors(breakdown),
        "metrics": metrics,
        "trajectory": trajectory.to_dict(),
        "evidence": evidence,
        "explanation": explanation.to_dict(),
    }


def financial_pulse(session: Session, persona: Persona, *, limit: int = 8,
                    as_of: datetime | None = None) -> list[dict]:
    """Ranked Financial Pulse entries for this persona."""
    as_of = as_of or datetime.now(timezone.utc)
    assets = list(session.scalars(select(MarketAssetORM)))
    entries = [e for e in (asset_pulse(session, persona, a, as_of=as_of) for a in assets)
               if e is not None]
    entries.sort(key=lambda e: -e["worldtune_score"])
    return entries[:limit]
