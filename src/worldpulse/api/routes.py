"""FastAPI routes wired to the repository layer.

Endpoints (per spec section 27):
  GET /health
  GET /events
  GET /events/{event_id}
  GET /events/{event_id}/similar
  GET /events/{event_id}/impact
  GET /predictions
  GET /predictions/live
  GET /predictions/{prediction_id}
  GET /performance
  GET /performance/horizons
  GET /performance/categories
  GET /assets/{symbol}/events
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from worldpulse.config import settings
from worldpulse.database.models import PredictionORM, WorldEventORM
from worldpulse.database.repository import get_default_session_factory
from worldpulse.evaluation.calibration import compute_calibration_table
from worldpulse.evaluation.scoring import compute_scoreboard
from worldpulse.events.classifier import RuleBasedEventClassifier
from worldpulse.events.schemas import ImpactScoreInputs, impact_candidate_score
from worldpulse.prediction.features import build_impact_inputs
from worldpulse.similarity.retrieval import retrieve_analogues
from worldpulse.similarity.ranking import rerank
from worldpulse.database.repository import _orm_to_event, get_events_as_of

router = APIRouter()


def get_db():
    factory = get_default_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.get("/health")
def health():
    """Liveness + which data mode WorldPulse is running in.

    `data_mode` is "FREE" under the default `WORLDPULSE_MODE=free`, meaning
    no paid data subscription is in use.
    """
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "data_mode": settings.data_mode,
        "worldpulse_mode": settings.worldpulse_mode,
        "event_providers": settings.provider_names(),
        "classifier": settings.ai_classifier,
    }


@router.get("/health/providers")
def provider_health():
    """Per-provider health.

    `status` is one of HEALTHY / DEGRADED / DISABLED / UNKNOWN. **DISABLED
    is a normal state**, not an error: it is what World Monitor, FIRMS and
    ACLED report when their (optional) key is absent, and what any provider
    not listed in `EVENT_PROVIDERS` reports. The endpoint therefore always
    returns HTTP 200.
    """
    from worldpulse.ingestion.providers import registry

    healths = registry.get_provider_health()
    active = [p.name for p in registry.get_active_providers()]
    counts: dict[str, int] = {}
    for health_record in healths:
        counts[health_record.status()] = counts.get(health_record.status(), 0) + 1
    return {
        "data_mode": settings.data_mode,
        "active_providers": active,
        "requested_providers": settings.provider_names(),
        "skipped": registry.get_skips(),
        "cost_groups": registry.provider_cost_groups(),
        "status_counts": counts,
        "providers": [h.to_dict() for h in healths],
    }


@router.get("/events")
def list_events(limit: int = 50, session: Session = Depends(get_db)):
    stmt = select(WorldEventORM).order_by(WorldEventORM.occurred_at.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_serialize_event(r) for r in rows]


@router.get("/events/{event_id}")
def get_event_detail(event_id: str, session: Session = Depends(get_db)):
    row = session.get(WorldEventORM, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    return _serialize_event(row)


@router.get("/events/{event_id}/evidence")
def get_event_evidence(event_id: str, session: Session = Depends(get_db)):
    """Provenance: every source that contributed to this event/cluster.

    Cross-source dedup merges e.g. a USGS earthquake, a GDELT article and
    an EONET entry into one cluster; this endpoint lists all of them rather
    than only the surviving record.
    """
    from worldpulse.database.repository import get_evidence_for_cluster, get_evidence_for_event

    row = session.get(WorldEventORM, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    evidence = get_evidence_for_event(session, event_id)
    cluster_evidence = (
        get_evidence_for_cluster(session, row.event_cluster_id) if row.event_cluster_id else []
    )
    return {
        "event_id": event_id,
        "event_cluster_id": row.event_cluster_id,
        "providers": sorted({e.provider for e in cluster_evidence or evidence}),
        "evidence": [
            {
                "provider": e.provider,
                "provider_event_id": e.provider_event_id,
                "source_url": e.source_url,
                "source_name": e.source_name,
                "observed_at": e.observed_at.isoformat(),
            }
            for e in (cluster_evidence or evidence)
        ],
    }


@router.get("/events/{event_id}/similar")
def get_similar_events(event_id: str, top_k: int = 10, session: Session = Depends(get_db)):
    row = session.get(WorldEventORM, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    target = _orm_to_event(row)
    candidates = get_events_as_of(session, as_of=target.occurred_at)
    candidates = [c for c in candidates if c.id != target.id]
    scored = retrieve_analogues(target, candidates, top_k=top_k)
    reranked = rerank(target, scored)
    return [
        {"event": _serialize_pydantic_event(c), "similarity_score": round(score, 4)}
        for c, score in reranked[:top_k]
    ]


@router.get("/events/{event_id}/impact")
def get_event_impact(event_id: str, session: Session = Depends(get_db)):
    row = session.get(WorldEventORM, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    target = _orm_to_event(row)
    recent = get_events_as_of(session, as_of=target.occurred_at, since=None)
    inputs: ImpactScoreInputs = build_impact_inputs(target, recent)
    score = impact_candidate_score(inputs)
    return {
        "event_id": event_id,
        "impact_candidate_score": round(score, 4),
        "components": inputs.model_dump(),
        "predicted_gate_pass": score >= 0.60,
    }


@router.get("/predictions")
def list_predictions(limit: int = 100, session: Session = Depends(get_db)):
    stmt = select(PredictionORM).order_by(PredictionORM.created_at.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_serialize_prediction(p) for p in rows]


@router.get("/predictions/live")
def list_live_predictions(limit: int = 100, session: Session = Depends(get_db)):
    stmt = (
        select(PredictionORM)
        .where(PredictionORM.resolved_at.is_(None))
        .order_by(PredictionORM.created_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    return [_serialize_prediction(p) for p in rows]


@router.get("/predictions/{prediction_id}")
def get_prediction_detail(prediction_id: str, session: Session = Depends(get_db)):
    row = session.get(PredictionORM, prediction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="prediction not found")
    return _serialize_prediction(row)


@router.get("/performance")
def performance(session: Session = Depends(get_db)):
    rows = session.execute(select(PredictionORM)).scalars().all()
    report = compute_scoreboard(list(rows))
    return {
        "total_predictions": report.total_predictions,
        "total_resolved": report.total_resolved,
        "coverage": round(report.coverage, 4),
        "directional_accuracy": round(report.directional_accuracy, 4) if report.directional_accuracy is not None else None,
        "precision_by_tier": {k: round(v, 4) for k, v in report.precision_by_tier.items()},
        "baseline_accuracy": {k: round(v, 4) for k, v in report.baseline_accuracy.items()},
    }


@router.get("/performance/horizons")
def performance_by_horizon(session: Session = Depends(get_db)):
    rows = session.execute(select(PredictionORM)).scalars().all()
    report = compute_scoreboard(list(rows))
    return {str(h): round(acc, 4) for h, acc in report.accuracy_by_horizon.items()}


@router.get("/performance/categories")
def performance_by_category(session: Session = Depends(get_db)):
    rows = session.execute(select(PredictionORM)).scalars().all()
    report = compute_scoreboard(list(rows))
    return {k: round(v, 4) for k, v in report.accuracy_by_domain.items()}


@router.get("/assets/{symbol}/events")
def events_for_asset(symbol: str, limit: int = 50, session: Session = Depends(get_db)):
    stmt = select(WorldEventORM).order_by(WorldEventORM.occurred_at.desc()).limit(500)
    rows = session.execute(stmt).scalars().all()
    matches = [r for r in rows if symbol in json.loads(r.potential_assets)]
    return [_serialize_event(r) for r in matches[:limit]]


# --- serialization helpers ---------------------------------------------

def _serialize_event(row: WorldEventORM) -> dict:
    return {
        "id": row.id,
        "occurred_at": row.occurred_at.isoformat(),
        "event_type": row.event_type,
        "event_subtype": row.event_subtype,
        "countries": json.loads(row.countries),
        "entities": json.loads(row.entities),
        "affected_channels": json.loads(row.affected_channels),
        "potential_assets": json.loads(row.potential_assets),
        "severity": row.severity,
        "headline": row.headline,
        "event_cluster_id": row.event_cluster_id,
        # --- provenance ---
        "provider": row.provider or None,
        "provider_event_id": row.provider_event_id or None,
        "event_domain": row.event_domain or row.event_type,
        "source_urls": json.loads(row.source_urls) if row.source_urls else [],
        "source_name": row.source_name or None,
        "locations": json.loads(row.locations) if row.locations else [],
        "latitude": row.latitude,
        "longitude": row.longitude,
        "industries": json.loads(row.industries) if row.industries else [],
        "commodities": json.loads(row.commodities) if row.commodities else [],
    }


def _serialize_pydantic_event(event) -> dict:
    return {
        "id": event.id,
        "occurred_at": event.occurred_at.isoformat(),
        "event_type": event.event_type if isinstance(event.event_type, str) else event.event_type.value,
        "event_subtype": event.event_subtype,
        "countries": event.countries,
        "headline": event.headline,
        "severity": event.severity,
    }


def _serialize_prediction(p: PredictionORM) -> dict:
    return {
        "id": p.id,
        "event_id": p.event_id,
        "symbol": p.symbol,
        "horizon_hours": p.horizon_hours,
        "direction": p.direction,
        "probability": p.probability,
        "expected_return": p.expected_return,
        "median_return": p.median_return,
        "p25_return": p.p25_return,
        "p75_return": p.p75_return,
        "sample_size": p.sample_size,
        "confidence_tier": p.confidence_tier,
        "event_domain": p.event_domain,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
        "actual_return": p.actual_return,
        "direction_correct": p.direction_correct,
        "result": p.result,
        "explanation": json.loads(p.explanation_json) if p.explanation_json else None,
    }
