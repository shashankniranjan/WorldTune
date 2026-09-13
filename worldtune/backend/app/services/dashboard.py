"""Dashboard aggregation -- the single home-screen response (spec section 32).

Shape, exactly as the spec specifies:

    {"persona", "summary", "financial_pulse", "career_pulse", "daily_tune",
     "generated_at"}

One endpoint rather than five round-trips, because the home screen is
useless in pieces: every number on it is ranked relative to the others by the
same score, and a client assembling it from separate calls could render a
partially-refreshed, internally inconsistent view.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import DISCLAIMER
from app.repositories.persona import get_persona
from app.schemas.persona import Persona
from app.services.career import career_pulse
from app.services.daily_tune import build_daily_tune
from app.services.financial import financial_pulse


def _summary(persona: Persona, financial: list[dict], skills: list[dict],
             jobs: list[dict]) -> dict:
    """The one-glance read. Counts of what is moving, plus the single
    highest-scoring item across both domains."""
    movers = [f for f in financial if abs(f["metrics"]["change_7d"]) >= 0.03]
    rising = [s for s in skills if s["metrics"]["direction"] == "growing"]
    cooling = [s for s in skills if s["metrics"]["direction"] == "declining"]

    everything = financial + skills
    headline = max(everything, key=lambda e: e["worldtune_score"]) if everything else None

    return {
        "headline": (
            f"{headline['label']}: {headline['explanation']['summary']}"
            if headline else "Not enough data yet -- seed or ingest signals to populate."
        ),
        "top_score": headline["worldtune_score"] if headline else 0.0,
        "assets_tracked": len(financial),
        "assets_moving": len(movers),
        "skills_tracked": len(skills),
        "skills_rising": len(rising),
        "skills_cooling": len(cooling),
        "job_matches": len(jobs),
        "persona_name": persona.name,
        "location": f"{persona.location.city}, {persona.location.country}".strip(", "),
    }


def build_dashboard(session: Session, *, persona_id: str | None = None,
                    limit: int = 6, as_of: datetime | None = None) -> dict:
    as_of = as_of or datetime.now(timezone.utc)
    persona = get_persona(session, persona_id)
    if persona is None:
        raise LookupError("No persona configured")

    financial = financial_pulse(session, persona, limit=limit, as_of=as_of)
    career = career_pulse(session, persona, limit=limit, as_of=as_of)
    skills, jobs = career["skill_signals"], career["job_matches"]
    daily = build_daily_tune(persona, financial=financial, skills=skills, jobs=jobs,
                             session=session, as_of=as_of)

    return {
        "persona": persona.model_dump(mode="json"),
        "summary": _summary(persona, financial, skills, jobs),
        "financial_pulse": financial,
        "career_pulse": {"skill_signals": skills, "job_matches": jobs},
        "daily_tune": daily,
        "generated_at": as_of.isoformat(),
        "model_version": settings.model_version,
        "demo_mode": settings.demo_mode,
        "disclaimer": DISCLAIMER,
    }
