"""Daily Tune -- the "what should I do next?" surface.

Four kinds, each answering a different verb, so the day's output is a short
list of actions rather than another feed:

    learn  -- the highest-scoring skill the persona does NOT have
    apply  -- the best-fitting open role
    watch  -- the watchlist/sector asset with the strongest move
    read   -- the single most relevant headline

Each item carries its own `why`, sourced from the same score breakdown that
ranked it. Nothing appears here that cannot point at its evidence.

The list is deliberately capped and diversified: one item per kind by
default. A recommendation list long enough to be comprehensive is a list
nobody acts on, and the persona's stated daily budget is 20 minutes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyRecommendationORM, NewsEventORM
from app.ranking.relevance import financial_relevance
from app.ranking.score import recency_score
from app.schemas.persona import Persona


def _news_pick(session: Session, persona: Persona, *, as_of: datetime) -> dict | None:
    """Most persona-relevant recent headline, recency-weighted.

    Relevance and recency are multiplied rather than added: a perfectly
    relevant month-old story and a fresh irrelevant one should both lose to a
    fresh relevant one, which addition would not guarantee.
    """
    rows = session.scalars(
        select(NewsEventORM).order_by(NewsEventORM.published_at.desc()).limit(120)
    ).all()
    best, best_score = None, 0.0
    for row in rows:
        relevance = financial_relevance(
            persona, symbol=(row.tickers or [""])[0],
            sector=(row.sectors or [""])[0],
            signal_text=row.title, entities=row.entities or [],
        )
        score = relevance.score * recency_score(row.published_at, as_of=as_of,
                                                half_life_hours=48.0)
        if score > best_score:
            best, best_score = row, score
    if best is None or best_score <= 0.0:
        return None
    return {
        "kind": "read",
        "title": best.title,
        "detail": f"{best.domain or best.source} - {best.published_at.date().isoformat()}",
        "why": (f"Matches your interests ({', '.join((best.sectors or ['technology'])[:2])}) "
                f"and is {_age_phrase(best.published_at, as_of)}."),
        "entity_type": "news",
        "entity_id": best.id,
        "url": best.url,
        "score": round(best_score * 100, 2),
    }


def _age_phrase(when: datetime, as_of: datetime) -> str:
    hours = max(0.0, (as_of - when).total_seconds() / 3600.0)
    if hours < 24:
        return f"{hours:.0f} hours old"
    return f"{hours / 24:.0f} days old"


def build_daily_tune(persona: Persona, *, financial: list[dict], skills: list[dict],
                     jobs: list[dict], session: Session,
                     as_of: datetime | None = None) -> list[dict]:
    as_of = as_of or datetime.now(timezone.utc)
    items: list[dict] = []

    learn_candidates = [s for s in skills if not s.get("already_have")]
    if learn_candidates:
        top = learn_candidates[0]
        m = top["metrics"]
        items.append({
            "kind": "learn",
            "title": f"Start on {top['label']}",
            "detail": (f"{m['skill_share']:.0%} of tracked postings mention it "
                       f"({m['change_30d']:+.1%} over 30 days, {m['direction']})."),
            "why": top["explanation"]["why_it_matters"],
            "entity_type": "skill",
            "entity_id": top["entity_id"],
            "url": "",
            "score": top["worldtune_score"],
        })

    if jobs:
        top = jobs[0]
        items.append({
            "kind": "apply",
            "title": f"{top['label']} at {top['company']}",
            "detail": f"{top['location']}"
                      + (f" - {top['seniority']}" if top.get("seniority") else ""),
            "why": "; ".join(top["score_breakdown"]["reasons"][:2])
                   or "Strongest overall fit against your profile today.",
            "entity_type": "job",
            "entity_id": top["entity_id"],
            "url": top.get("url", ""),
            "score": top["worldtune_score"],
        })

    if financial:
        top = financial[0]
        m = top["metrics"]
        items.append({
            "kind": "watch",
            "title": f"{top['label']} is {m['direction']} over {m['horizon_days']} days",
            "detail": (f"{m['change_24h']:+.2%} in 24h, {m['change_7d']:+.2%} over 7 days; "
                       f"{m['probability']:.0%} probability, confidence {m['confidence']:.2f}."),
            "why": top["explanation"]["why_it_matters"],
            "entity_type": "asset",
            "entity_id": top["entity_id"],
            "url": "",
            "score": top["worldtune_score"],
        })

    news_item = _news_pick(session, persona, as_of=as_of)
    if news_item:
        items.append(news_item)
    return items


def persist_daily_tune(session: Session, persona_id: str, items: list[dict], *,
                       for_date: datetime | None = None, is_demo: bool = False) -> int:
    """Store today's recommendations. Replaces the same day's rows so a
    re-run is an update, not an append."""
    day = (for_date or datetime.now(timezone.utc)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    existing = session.scalars(
        select(DailyRecommendationORM)
        .where(DailyRecommendationORM.persona_id == persona_id)
        .where(DailyRecommendationORM.for_date == day)
    ).all()
    for row in existing:
        session.delete(row)
    for item in items:
        session.add(DailyRecommendationORM(
            id=str(uuid.uuid4()), persona_id=persona_id, for_date=day,
            kind=item["kind"], title=item["title"], detail=item.get("detail", ""),
            why=item.get("why", ""), entity_type=item.get("entity_type", ""),
            entity_id=item.get("entity_id", ""), url=item.get("url", ""),
            score=float(item.get("score", 0.0)), is_demo=is_demo,
        ))
    session.flush()
    return len(items)
