"""WorldTune HTTP API (spec section 31).

Every read endpoint is a thin adapter over a service function: parse and
sanitize input, call the service, return its dict. No analysis lives here.
That keeps the whole scoring/trajectory surface testable without a web
client, and makes the API replaceable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.security import clamp_limit, sanitize_query
from app.config import settings
from app.db import get_db
from app.models import (
    DISCLAIMER,
    DailyRecommendationORM,
    JobORM,
    MarketAssetORM,
    NewsEventORM,
    PredictionORM,
    PredictionResultORM,
    SignalORM,
    SkillORM,
    TechnologyEventORM,
)
from app.predictions.evaluate import evaluate_classification, ranking_stability
from app.predictions.store import CAREER_OUTCOMES, FINANCIAL_OUTCOMES, resolved_pairs
from app.providers import registry
from app.repositories.persona import get_persona, upsert_persona
from app.schemas.persona import Persona, PersonaUpdate
from app.seed.demo import counts as seed_counts
from app.seed.demo import seed_demo
from app.services.career import career_pulse, job_matches, skill_signals, technology_velocity
from app.services.daily_tune import build_daily_tune, persist_daily_tune
from app.services.dashboard import build_dashboard
from app.services.financial import asset_pulse, financial_pulse

router = APIRouter()


def _persona_or_404(session: Session, persona_id: str | None = None) -> Persona:
    persona = get_persona(session, persona_id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No persona configured. POST /api/system/seed first.")
    return persona


# --- health / system ---------------------------------------------------------

@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "worldtune", "version": "0.1.0",
            "demo_mode": settings.demo_mode}


@router.get("/api/system/data-sources", tags=["system"])
def data_sources() -> dict:
    """Per-provider demo-vs-live status."""
    return registry.describe_all()


@router.get("/api/system/stats", tags=["system"])
def system_stats(session: Session = Depends(get_db)) -> dict:
    return {"demo_mode": settings.demo_mode, "model_version": settings.model_version,
            "counts": seed_counts(session), "disclaimer": DISCLAIMER}


@router.post("/api/system/seed", tags=["system"])
def run_seed(force: bool = Query(False), session: Session = Depends(get_db)) -> dict:
    result = seed_demo(session, force=force)
    session.commit()
    return result


# --- persona -----------------------------------------------------------------

@router.get("/api/persona", response_model=Persona, tags=["persona"])
def read_persona(persona_id: str | None = Query(None),
                 session: Session = Depends(get_db)) -> Persona:
    return _persona_or_404(session, persona_id)


@router.put("/api/persona", response_model=Persona, tags=["persona"])
def update_persona(payload: PersonaUpdate, persona_id: str | None = Query(None),
                   session: Session = Depends(get_db)) -> Persona:
    persona = upsert_persona(session, payload, persona_id=persona_id)
    session.commit()
    return persona


# --- dashboard ---------------------------------------------------------------

@router.get("/api/dashboard", tags=["dashboard"])
def dashboard(limit: int = Query(6, ge=1, le=50), persona_id: str | None = Query(None),
              session: Session = Depends(get_db)) -> dict:
    """The single aggregated home-screen response (spec section 32)."""
    try:
        return build_dashboard(session, persona_id=persona_id, limit=clamp_limit(limit, default=6))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- financial ---------------------------------------------------------------

@router.get("/api/financial/pulse", tags=["financial"])
def financial(limit: int = Query(8, ge=1, le=50), persona_id: str | None = Query(None),
              session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    entries = financial_pulse(session, persona, limit=clamp_limit(limit, default=8))
    return {"persona_id": persona.id, "count": len(entries), "entries": entries,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": DISCLAIMER}


@router.get("/api/financial/assets", tags=["financial"])
def list_assets(session: Session = Depends(get_db)) -> dict:
    rows = session.scalars(select(MarketAssetORM).order_by(MarketAssetORM.symbol)).all()
    return {"count": len(rows),
            "assets": [{"symbol": r.symbol, "name": r.name, "asset_class": r.asset_class,
                        "sector": r.sector, "is_demo": r.is_demo} for r in rows]}


@router.get("/api/financial/assets/{symbol}", tags=["financial"])
def asset_detail(symbol: str, persona_id: str | None = Query(None),
                 session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    asset = session.get(MarketAssetORM, sanitize_query(symbol, max_length=16).upper())
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Unknown asset '{symbol}'")
    entry = asset_pulse(session, persona, asset)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Not enough price history for '{symbol}'")
    return entry


# --- career ------------------------------------------------------------------

@router.get("/api/career/pulse", tags=["career"])
def career(limit: int = Query(8, ge=1, le=50), persona_id: str | None = Query(None),
           session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    pulse = career_pulse(session, persona, limit=clamp_limit(limit, default=8))
    return {"persona_id": persona.id, **pulse,
            "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/api/career/skills", tags=["career"])
def career_skills(limit: int = Query(12, ge=1, le=100),
                  scope_type: str = Query("global", pattern="^(global|role_family|location)$"),
                  scope_value: str = Query(""), persona_id: str | None = Query(None),
                  session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    entries = skill_signals(session, persona, limit=clamp_limit(limit, default=12),
                            scope_type=scope_type,
                            scope_value=sanitize_query(scope_value, max_length=60))
    return {"scope": {"type": scope_type, "value": scope_value},
            "count": len(entries), "entries": entries}


@router.get("/api/career/jobs", tags=["career"])
def career_jobs(limit: int = Query(10, ge=1, le=50), days: int = Query(30, ge=1, le=180),
                q: str = Query(""), persona_id: str | None = Query(None),
                session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    entries = job_matches(session, persona, limit=clamp_limit(limit, default=10), days=days)
    needle = sanitize_query(q).lower()
    if needle:
        entries = [e for e in entries if needle in e["label"].lower()
                   or needle in (e.get("company") or "").lower()]
    return {"count": len(entries), "query": needle, "entries": entries}


@router.get("/api/career/skills/{skill_id}", tags=["career"])
def skill_detail(skill_id: str, persona_id: str | None = Query(None),
                 session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    clean = sanitize_query(skill_id, max_length=40)
    if session.get(SkillORM, clean) is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill '{skill_id}'")
    entries = [e for e in skill_signals(session, persona, limit=200)
               if e["entity_id"] == clean]
    if not entries:
        raise HTTPException(status_code=404, detail=f"No metrics yet for '{skill_id}'")
    return entries[0]


# --- technology / news / signals ---------------------------------------------

@router.get("/api/technology/signals", tags=["technology"])
def technology_signals(limit: int = Query(20, ge=1, le=100),
                       session: Session = Depends(get_db)) -> dict:
    """Latest snapshot per technology, with the derived per-skill velocity."""
    rows = session.scalars(
        select(TechnologyEventORM).order_by(TechnologyEventORM.observed_at)
    ).all()
    latest: dict[str, TechnologyEventORM] = {}
    for row in rows:
        latest[row.name] = row
    velocity = technology_velocity(session)
    entries = [{
        "name": r.name, "category": r.category, "title": r.title, "url": r.url,
        "source": r.source, "observed_at": r.observed_at.isoformat(),
        "stars": r.stars, "stars_7d_delta": r.stars_7d_delta, "points": r.points,
        "related_skills": r.related_skills or [],
        "skill_velocity": {s: round(velocity.get(s, 0.0), 5)
                           for s in (r.related_skills or [])},
    } for r in latest.values()]
    entries.sort(key=lambda e: -abs(e["stars_7d_delta"]))
    return {"count": len(entries), "entries": entries[:clamp_limit(limit, default=20)]}


@router.get("/api/news", tags=["news"])
def news(limit: int = Query(20, ge=1, le=100), q: str = Query(""),
         days: int = Query(14, ge=1, le=120), session: Session = Depends(get_db)) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (select(NewsEventORM).where(NewsEventORM.published_at >= since)
            .order_by(NewsEventORM.published_at.desc()))
    rows = session.scalars(stmt).all()
    needle = sanitize_query(q).lower()
    if needle:
        rows = [r for r in rows if needle in r.title.lower()]
    rows = rows[:clamp_limit(limit, default=20)]
    return {"count": len(rows), "query": needle, "entries": [{
        "id": r.id, "title": r.title, "url": r.url, "source": r.source,
        "domain": r.domain, "published_at": r.published_at.isoformat(),
        "sentiment": round(r.sentiment, 3), "entities": r.entities or [],
        "tickers": r.tickers or [], "sectors": r.sectors or [],
    } for r in rows]}


@router.get("/api/signals", tags=["signals"])
def signals(limit: int = Query(25, ge=1, le=100), signal_type: str = Query(""),
            entity_id: str = Query(""), session: Session = Depends(get_db)) -> dict:
    """The generic signal spine -- one shape across news/market/job/technology."""
    stmt = select(SignalORM).order_by(SignalORM.timestamp.desc())
    kind = sanitize_query(signal_type, max_length=20)
    if kind:
        stmt = stmt.where(SignalORM.signal_type == kind)
    entity = sanitize_query(entity_id, max_length=60)
    if entity:
        stmt = stmt.where(SignalORM.entity_id == entity)
    rows = session.scalars(stmt.limit(clamp_limit(limit, default=25))).all()
    return {"count": len(rows), "entries": [{
        "id": r.id, "signal_type": r.signal_type, "entity_type": r.entity_type,
        "entity_id": r.entity_id, "timestamp": r.timestamp.isoformat(), "title": r.title,
        "description": r.description, "source": r.source, "sentiment": round(r.sentiment, 3),
        "metadata": r.meta or {},
    } for r in rows]}


# --- daily tune --------------------------------------------------------------

@router.get("/api/daily-tune", tags=["daily-tune"])
def daily_tune(persona_id: str | None = Query(None), persist: bool = Query(False),
               session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    now = datetime.now(timezone.utc)
    financial = financial_pulse(session, persona, limit=6, as_of=now)
    pulse = career_pulse(session, persona, limit=8, as_of=now)
    items = build_daily_tune(persona, financial=financial,
                             skills=pulse["skill_signals"], jobs=pulse["job_matches"],
                             session=session, as_of=now)
    if persist:
        persist_daily_tune(session, persona.id, items, for_date=now,
                           is_demo=settings.demo_mode)
        session.commit()
    return {"persona_id": persona.id, "for_date": now.date().isoformat(),
            "count": len(items), "items": items}


@router.get("/api/daily-tune/history", tags=["daily-tune"])
def daily_tune_history(limit: int = Query(20, ge=1, le=100),
                       persona_id: str | None = Query(None),
                       session: Session = Depends(get_db)) -> dict:
    persona = _persona_or_404(session, persona_id)
    rows = session.scalars(
        select(DailyRecommendationORM)
        .where(DailyRecommendationORM.persona_id == persona.id)
        .order_by(DailyRecommendationORM.for_date.desc())
        .limit(clamp_limit(limit, default=20))
    ).all()
    return {"count": len(rows), "items": [{
        "for_date": r.for_date.date().isoformat(), "kind": r.kind, "title": r.title,
        "detail": r.detail, "why": r.why, "url": r.url, "score": r.score,
    } for r in rows]}


# --- predictions -------------------------------------------------------------

@router.get("/api/predictions", tags=["predictions"])
def list_predictions(limit: int = Query(25, ge=1, le=200), domain: str = Query(""),
                     entity_id: str = Query(""), session: Session = Depends(get_db)) -> dict:
    stmt = select(PredictionORM).order_by(PredictionORM.created_at.desc())
    dom = sanitize_query(domain, max_length=20)
    if dom:
        stmt = stmt.where(PredictionORM.domain == dom)
    ent = sanitize_query(entity_id, max_length=60)
    if ent:
        stmt = stmt.where(PredictionORM.entity_id == ent)
    rows = session.scalars(stmt.limit(clamp_limit(limit, default=25))).all()
    results = {
        r.prediction_id: r for r in session.scalars(
            select(PredictionResultORM).where(
                PredictionResultORM.prediction_id.in_([p.id for p in rows]))
        ).all()
    }
    return {"count": len(rows), "disclaimer": DISCLAIMER, "entries": [{
        "id": p.id, "domain": p.domain, "entity_type": p.entity_type,
        "entity_id": p.entity_id, "created_at": p.created_at.isoformat(),
        "horizon_days": p.horizon_days, "predicted_direction": p.predicted_direction,
        "predicted_probability": p.predicted_probability, "confidence": p.confidence,
        "rationale": p.rationale, "model_version": p.model_version,
        "resolves_at": p.resolves_at.isoformat(),
        "result": ({"actual_outcome": results[p.id].actual_outcome,
                    "actual_value": results[p.id].actual_value,
                    "correct": results[p.id].correct,
                    "brier": round(results[p.id].brier, 4),
                    "resolved_at": results[p.id].resolved_at.isoformat()}
                   if p.id in results else None),
    } for p in rows]}


@router.get("/api/predictions/accuracy", tags=["predictions"])
def prediction_accuracy(domain: str = Query("financial"),
                        session: Session = Depends(get_db)) -> dict:
    """Evaluation metrics over resolved predictions (spec section 16)."""
    dom = sanitize_query(domain, max_length=20) or "financial"
    pairs = resolved_pairs(session, domain=dom)
    if not pairs:
        return {"domain": dom, "n": 0,
                "message": "No resolved predictions yet.", "disclaimer": DISCLAIMER}
    predicted = [p.predicted_direction for p, _ in pairs]
    actual = [r.actual_outcome for _, r in pairs]
    probabilities = [p.predicted_probability for p, _ in pairs]
    labels = FINANCIAL_OUTCOMES if dom == "financial" else CAREER_OUTCOMES
    metrics = evaluate_classification(predicted, actual, probabilities, labels)
    return {"domain": dom, "model_version": settings.model_version,
            **metrics.to_dict(), "disclaimer": DISCLAIMER}


@router.get("/api/predictions/stability", tags=["predictions"])
def prediction_stability(limit: int = Query(10, ge=1, le=50),
                         persona_id: str | None = Query(None),
                         session: Session = Depends(get_db)) -> dict:
    """Top-k ranking stability between the current and the previous day's
    persisted Daily Tune -- the recommender-churn diagnostic."""
    persona = _persona_or_404(session, persona_id)
    rows = session.scalars(
        select(DailyRecommendationORM)
        .where(DailyRecommendationORM.persona_id == persona.id)
        .order_by(DailyRecommendationORM.for_date.desc())
    ).all()
    by_date: dict[str, list[str]] = {}
    for row in rows:
        by_date.setdefault(row.for_date.date().isoformat(), []).append(row.entity_id)
    dates = sorted(by_date, reverse=True)
    if len(dates) < 2:
        return {"n_days": len(dates), "stability": None,
                "message": "Need at least two persisted Daily Tune days."}
    return {"n_days": len(dates), "compared": dates[:2],
            "stability": ranking_stability(by_date[dates[1]], by_date[dates[0]], k=limit)}


# --- counts helper used by tests ---------------------------------------------

@router.get("/api/system/table-counts", tags=["system"])
def table_counts(session: Session = Depends(get_db)) -> dict:
    return {
        "jobs": int(session.scalar(select(func.count()).select_from(JobORM)) or 0),
        "news_events": int(session.scalar(select(func.count()).select_from(NewsEventORM)) or 0),
        "signals": int(session.scalar(select(func.count()).select_from(SignalORM)) or 0),
    }
