"""Persisted refresh controls shared by the scheduler and the dashboard UI."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.db import session_scope
from app.models import WorldShiftRefreshRunORM, WorldShiftRuntimeConfigORM
from app.schemas.world_shift import RefreshConfiguration

ALLOWED_INTERVALS = (300, 3600, 43200, 86400)


def _row(session) -> WorldShiftRuntimeConfigORM:
    row = session.get(WorldShiftRuntimeConfigORM, 1)
    if row is None:
        row = WorldShiftRuntimeConfigORM(
            id=1,
            interval_seconds=settings.world_shift_refresh_interval_seconds,
            web_research_enabled=settings.world_shift_web_research_enabled,
            web_results_per_shift=settings.world_shift_web_results_per_shift,
        )
        session.add(row)
        session.flush()
    return row


def get_runtime_values() -> tuple[int, bool, int]:
    with session_scope() as session:
        row = _row(session)
        return row.interval_seconds, row.web_research_enabled, row.web_results_per_shift


def get_refresh_configuration() -> RefreshConfiguration:
    with session_scope() as session:
        row = _row(session)
        latest = session.scalars(select(WorldShiftRefreshRunORM).order_by(
            WorldShiftRefreshRunORM.created_at.desc()
        )).first()
        next_refresh = None
        if latest:
            created = latest.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            next_refresh = (created + timedelta(seconds=row.interval_seconds)).isoformat()
        return RefreshConfiguration(
            intervalSeconds=row.interval_seconds,
            webResearchEnabled=row.web_research_enabled,
            webResultsPerShift=row.web_results_per_shift,
            allowedIntervals=list(ALLOWED_INTERVALS),
            nextRefreshAt=next_refresh,
        )


def update_refresh_configuration(*, interval_seconds: int, web_research_enabled: bool,
                                 web_results_per_shift: int) -> RefreshConfiguration:
    if interval_seconds not in ALLOWED_INTERVALS:
        raise ValueError(f"interval must be one of {ALLOWED_INTERVALS}")
    with session_scope() as session:
        row = _row(session)
        row.interval_seconds = interval_seconds
        row.web_research_enabled = web_research_enabled
        row.web_results_per_shift = web_results_per_shift
        row.updated_at = datetime.now(timezone.utc)
    return get_refresh_configuration()
