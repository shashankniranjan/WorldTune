"""Persona persistence.

The ORM row stores the structured sub-objects as JSON; this module is the
only place that converts between that and the validated pydantic `Persona`.
The embedding is recomputed on every write so a persona edit immediately
changes what the user sees -- a stale embedding would silently keep ranking
against the old profile.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PersonaORM, UserORM
from app.ranking.embedding import embed_text
from app.schemas.persona import (
    DEMO_PERSONA,
    DEMO_USER_EMAIL,
    DEMO_USER_ID,
    CareerProfile,
    FinancialProfile,
    Location,
    Persona,
    PersonaBase,
    Preferences,
)


def to_schema(row: PersonaORM) -> Persona:
    return Persona(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        location=Location(**(row.location or {})),
        career=CareerProfile(**(row.career or {})),
        financial=FinancialProfile(**(row.financial or {})),
        preferences=Preferences(**(row.preferences or {})),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _persona_embedding_text(persona: PersonaBase) -> str:
    return " ".join(filter(None, [
        persona.name, persona.career.current_role, persona.career.industry,
        " ".join(persona.career.target_roles), " ".join(persona.career.skills),
        " ".join(persona.financial.watchlist), " ".join(persona.financial.sectors),
        " ".join(persona.financial.asset_classes),
        " ".join(persona.preferences.learning_topics),
        persona.location.city, persona.location.country,
    ]))


def get_persona(session: Session, persona_id: str | None = None) -> Persona | None:
    target = persona_id or settings.default_persona_id
    row = session.get(PersonaORM, target)
    if row is None:
        # Multi-persona-ready: fall back to "the first persona" rather than
        # assuming the demo id exists, so a differently-seeded DB still works.
        row = session.scalars(select(PersonaORM).order_by(PersonaORM.created_at).limit(1)).first()
    return to_schema(row) if row else None


def list_personas(session: Session) -> list[Persona]:
    return [to_schema(r) for r in session.scalars(select(PersonaORM)).all()]


def upsert_persona(session: Session, data: PersonaBase, *, persona_id: str | None = None,
                   user_id: str = DEMO_USER_ID) -> Persona:
    target = persona_id or settings.default_persona_id
    row = session.get(PersonaORM, target)
    now = datetime.now(timezone.utc)
    if row is None:
        row = PersonaORM(id=target, user_id=user_id, created_at=now)
        session.add(row)
    row.name = data.name
    row.location = data.location.model_dump()
    row.career = data.career.model_dump()
    row.financial = data.financial.model_dump()
    row.preferences = data.preferences.model_dump()
    row.embedding = embed_text(_persona_embedding_text(data))
    row.updated_at = now
    session.flush()
    return to_schema(row)


def ensure_demo_persona(session: Session) -> Persona:
    """Idempotent: create the demo user + persona if absent, else return it."""
    if session.get(UserORM, DEMO_USER_ID) is None:
        session.add(UserORM(id=DEMO_USER_ID, email=DEMO_USER_EMAIL,
                            display_name="WorldTune Demo User"))
        session.flush()
    existing = session.get(PersonaORM, settings.default_persona_id)
    if existing is not None:
        return to_schema(existing)
    return upsert_persona(session, DEMO_PERSONA, persona_id=settings.default_persona_id,
                          user_id=DEMO_USER_ID)
