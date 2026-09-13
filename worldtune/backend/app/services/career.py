"""Career Pulse -- "what's shifting in my field, and what should I do about it?"

Two rankings, both persona-scored with the same section-14 formula:

  * **skill signals** -- which skills are heating up or cooling down in job
    postings, judged against what the persona already has and what they said
    they want to learn. This is where the "where is it heading" question gets
    its 7/30/90-day answer.
  * **job matches** -- specific openings ranked by fit, so the pulse ends in
    something actionable rather than a trend chart.

Technology signals (GitHub / HN) feed in as a *leading* term on skill
trajectory: code and discussion activity moves before job descriptions do.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import trend as T
from app.analytics.trajectory import career_trajectory, career_trajectory_multi
from app.llm.explainer import get_explainer
from app.models import JobORM, JobSkillORM, SkillORM, TechnologyEventORM
from app.ranking.relevance import career_relevance, skill_relevance
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
from app.skills.metrics import latest_metrics, skill_share_series


def technology_velocity(session: Session, *, as_of: datetime | None = None
                        ) -> dict[str, float]:
    """{skill_id: fractional star/discussion growth} from technology snapshots.

    Computed by differencing the earliest and latest snapshot of each
    technology, then attributing that growth to every skill the technology
    implies. A skill touched by several technologies takes the strongest
    signal rather than an average -- one clearly accelerating technology is
    the news, and averaging it against three flat ones would hide it.
    """
    as_of = as_of or datetime.now(timezone.utc)
    rows = list(session.scalars(
        select(TechnologyEventORM).order_by(TechnologyEventORM.observed_at)
    ))
    by_name: dict[str, list[TechnologyEventORM]] = {}
    for row in rows:
        by_name.setdefault(row.name, []).append(row)

    velocity: dict[str, float] = {}
    for name, snapshots in by_name.items():
        if len(snapshots) < 2:
            continue
        first, last = snapshots[0], snapshots[-1]
        base = first.stars or first.points or 0.0
        if base <= 0:
            continue
        current = last.stars or last.points or 0.0
        weeks = max(1.0, (last.observed_at - first.observed_at).days / 7.0)
        growth = (current / base - 1.0) / weeks     # per-week fractional growth
        for skill_id in (last.related_skills or []):
            if abs(growth) > abs(velocity.get(skill_id, 0.0)):
                velocity[skill_id] = float(growth)
    return velocity


def skill_signals(session: Session, persona: Persona, *, limit: int = 8,
                  as_of: datetime | None = None, scope_type: str = "global",
                  scope_value: str = "") -> list[dict]:
    as_of = as_of or datetime.now(timezone.utc)
    metrics = latest_metrics(session, scope_type=scope_type, scope_value=scope_value)
    if not metrics:
        return []
    velocity = technology_velocity(session, as_of=as_of)
    skills = {s.id: s for s in session.scalars(select(SkillORM))}
    explainer = get_explainer()

    entries: list[dict] = []
    for skill_id, metric in metrics.items():
        skill = skills.get(skill_id)
        name = skill.name if skill else skill_id
        series = skill_share_series(session, skill_id, scope_type=scope_type,
                                    scope_value=scope_value)
        tech_v = velocity.get(skill_id, 0.0)
        trajectory = career_trajectory(series, horizon_days=30, tech_velocity=tech_v)
        horizons = career_trajectory_multi(series, tech_velocity=tech_v)
        relevance = skill_relevance(persona, skill_id=skill_id, skill_name=name)

        evidence = [
            {"type": "job-postings", "source": "worldtune:skill-metrics",
             "detail": (f"{name} appears in {metric.skill_mentions} of {metric.job_count} "
                        f"tracked postings ({metric.skill_share:.0%} share)"),
             "observed_at": metric.as_of.isoformat()},
            {"type": "trend", "source": "worldtune:trend",
             "detail": (f"7d {metric.change_7d:+.1%}, 30d {metric.change_30d:+.1%}, "
                        f"z-score {metric.zscore:+.2f}"),
             "observed_at": metric.as_of.isoformat()},
        ]
        if abs(tech_v) > 0.001:
            evidence.append({
                "type": "technology", "source": "worldtune:technology",
                "detail": f"related technology activity {tech_v:+.1%}/week",
                "observed_at": as_of.isoformat()})

        breakdown = compute_score(
            persona_relevance=relevance.score,
            trend_momentum=trend_momentum_score(metric.change_7d, metric.acceleration,
                                                metric.zscore),
            evidence_strength=evidence_strength_score(
                n_sources=len(evidence), n_observations=metric.job_count,
                corroborating_signals=metric.skill_mentions),
            novelty=novelty_score(zscore=metric.zscore,
                                  is_new_entity=relevance.components.get("already_have", 0.0) == 0.0),
            recency=recency_score(metric.as_of, as_of=as_of, half_life_hours=72.0),
            prediction_confidence=prediction_confidence_score(trajectory.confidence,
                                                              trajectory.probability),
            relevance_components=relevance.components,
            evidence=evidence,
            reasons=relevance.reasons,
        )

        metrics_payload = {
            "skill_mentions": metric.skill_mentions,
            "job_count": metric.job_count,
            "skill_share": round(metric.skill_share, 4),
            "change_7d": round(metric.change_7d, 6),
            "change_30d": round(metric.change_30d, 6),
            "acceleration": round(metric.acceleration, 6),
            "zscore": round(metric.zscore, 4),
            "tech_velocity": round(tech_v, 6),
            "direction": trajectory.direction,
            "probability": trajectory.probability,
            "confidence": trajectory.confidence,
        }
        explanation = explainer.explain(
            persona={"skills": persona.career.skills,
                     "target_roles": persona.career.target_roles,
                     "learning_topics": persona.preferences.learning_topics,
                     "city": persona.location.city},
            signal={"domain": "career", "label": name, "entity_id": skill_id,
                    "category": skill.category if skill else ""},
            metrics=metrics_payload,
            evidence=evidence,
            score=breakdown.to_dict(),
        )
        entries.append({
            "entity_type": "skill",
            "entity_id": skill_id,
            "label": name,
            "category": skill.category if skill else "",
            "already_have": bool(relevance.components.get("already_have")),
            "worldtune_score": breakdown.score,
            "score_breakdown": breakdown.to_dict(),
            "top_contributors": top_contributors(breakdown),
            "metrics": metrics_payload,
            "trajectory": trajectory.to_dict(),
            "trajectory_by_horizon": horizons,
            "evidence": evidence,
            "explanation": explanation.to_dict(),
        })
    entries.sort(key=lambda e: -e["worldtune_score"])
    return entries[:limit]


def job_matches(session: Session, persona: Persona, *, limit: int = 8,
                as_of: datetime | None = None, days: int = 30) -> list[dict]:
    """Specific openings ranked by persona fit."""
    as_of = as_of or datetime.now(timezone.utc)
    since = as_of - timedelta(days=days)
    jobs = list(session.scalars(
        select(JobORM).where(JobORM.posted_at >= since).order_by(JobORM.posted_at.desc())
    ))
    if not jobs:
        return []
    links = list(session.execute(
        select(JobSkillORM.job_id, JobSkillORM.skill_id)
        .where(JobSkillORM.job_id.in_([j.id for j in jobs]))
    ).all())
    skills_by_job: dict[str, list[str]] = {}
    for job_id, skill_id in links:
        skills_by_job.setdefault(job_id, []).append(skill_id)

    # Posting velocity for the persona's role families, used as the
    # "job-market momentum" sub-score called for in spec section 14.
    family_momentum = _role_family_momentum(jobs, as_of=as_of)

    entries: list[dict] = []
    for job in jobs:
        job_skills = skills_by_job.get(job.id, [])
        relevance = career_relevance(
            persona, title=job.title, skills=job_skills, location=job.location,
            remote=job.remote, seniority=job.seniority,
            signal_text=job.description[:800],
        )
        momentum = family_momentum.get(job.role_family, 0.0)
        evidence = [
            {"type": "job", "source": job.source,
             "detail": f"{job.title} at {job.company} ({job.location})",
             "url": job.url, "observed_at": job.posted_at.isoformat()},
            {"type": "skills", "source": "worldtune:extraction",
             "detail": f"requires {', '.join(job_skills[:6]) or 'unspecified skills'}",
             "observed_at": job.posted_at.isoformat()},
            {"type": "market", "source": "worldtune:trend",
             "detail": f"{job.role_family} posting velocity {momentum:+.1%} over 7 days",
             "observed_at": as_of.isoformat()},
        ]
        breakdown = compute_score(
            persona_relevance=relevance.score,
            trend_momentum=trend_momentum_score(momentum),
            evidence_strength=evidence_strength_score(
                n_sources=1, n_observations=len(job_skills) * 5,
                corroborating_signals=len(job_skills)),
            novelty=novelty_score(is_new_entity=True, zscore=momentum * 5.0),
            recency=recency_score(job.posted_at, as_of=as_of, half_life_hours=96.0),
            # A job match is a fit assessment, not a forecast; its
            # "prediction confidence" is how confident the *fit* is, which is
            # exactly the relevance score. Stated here so the 0.10 weight is
            # not mistaken for a hidden forecast.
            prediction_confidence=relevance.score,
            relevance_components=relevance.components,
            evidence=evidence,
            reasons=relevance.reasons,
        )
        entries.append({
            "entity_type": "job",
            "entity_id": job.id,
            "label": job.title,
            "company": job.company,
            "location": job.location,
            "remote": job.remote,
            "seniority": job.seniority,
            "role_family": job.role_family,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "url": job.url,
            "posted_at": job.posted_at.isoformat(),
            "matched_skills": job_skills,
            "worldtune_score": breakdown.score,
            "score_breakdown": breakdown.to_dict(),
            "top_contributors": top_contributors(breakdown),
            "evidence": evidence,
        })
    entries.sort(key=lambda e: -e["worldtune_score"])
    return entries[:limit]


def _role_family_momentum(jobs: list[JobORM], *, as_of: datetime) -> dict[str, float]:
    """7-day posting-count change per role family."""
    by_family: dict[str, list[datetime]] = {}
    for job in jobs:
        by_family.setdefault(job.role_family, []).append(job.posted_at)
    out: dict[str, float] = {}
    for family, stamps in by_family.items():
        counts = T.daily_counts(stamps, as_of=as_of, days=30)
        # Compare the trailing week against the one before it; raw day-over-day
        # posting counts are far too spiky to read directly.
        recent, prior = sum(counts[-7:]), sum(counts[-14:-7])
        out[family] = float(recent / prior - 1.0) if prior else 0.0
    return out


def career_pulse(session: Session, persona: Persona, *, limit: int = 8,
                 as_of: datetime | None = None) -> dict:
    return {
        "skill_signals": skill_signals(session, persona, limit=limit, as_of=as_of),
        "job_matches": job_matches(session, persona, limit=limit, as_of=as_of),
    }
