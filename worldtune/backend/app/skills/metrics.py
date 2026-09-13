"""Skill demand metrics -- the Career Pulse measurement layer.

Computes, per skill and per day, over a trailing window:

    skill_mentions : postings in the window mentioning the skill
    job_count      : postings in the window (the denominator)
    skill_share    : mentions / job_count

`skill_share`, not raw mentions, is the quantity everything downstream uses.
Raw counts confound "this skill is in demand" with "there were more job
postings this week", and a hiring product that mistakes a busy Tuesday for a
technology shift is worthless. Share normalizes that away.

The window is *trailing* (default 30 days) rather than per-day: daily posting
volume on a board this size is too spiky for a one-day share to mean
anything, and a trailing window is the standard fix. 30 rather than 14 was
chosen after observing that a fortnight's postings on a board this size gives
a denominator around 10 -- a share computed on 10 samples swings by 10
percentage points when one posting changes, which is noise presented as a
trend.

Scope lets the same machinery answer "Iceberg demand globally", "...in
data-engineering roles" and "...in Bengaluru" without special-casing, which
is what spec section 9's role- and location-specific demand asks for.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.trend import acceleration as accel_fn
from app.analytics.trend import pct_change_over, zscore
from app.models import JobORM, JobSkillORM, SkillMetricORM

DEFAULT_WINDOW_DAYS = 30


def _job_rows(session: Session, *, scope_type: str, scope_value: str) -> list[tuple]:
    """(job_id, posted_at) for the scope. Location scope matches on substring
    because boards spell the same city many ways ("Bengaluru, India",
    "Bangalore, KA")."""
    stmt = select(JobORM.id, JobORM.posted_at)
    if scope_type == "role_family" and scope_value:
        stmt = stmt.where(JobORM.role_family == scope_value)
    elif scope_type == "location" and scope_value:
        stmt = stmt.where(JobORM.location.ilike(f"%{scope_value}%"))
    return list(session.execute(stmt).all())


def compute_skill_series(
    session: Session,
    *,
    as_of: datetime | None = None,
    days: int = 60,
    window_days: int = DEFAULT_WINDOW_DAYS,
    scope_type: str = "global",
    scope_value: str = "",
) -> dict[str, dict]:
    """Return {skill_id: {"dates": [...], "share": [...], "mentions": [...],
    "job_counts": [...]}} -- dense daily series ending at `as_of`."""
    as_of = as_of or datetime.now(timezone.utc)
    jobs = _job_rows(session, scope_type=scope_type, scope_value=scope_value)
    if not jobs:
        return {}
    job_ids = {j[0] for j in jobs}
    posted_by_job = {j[0]: j[1] for j in jobs}

    links = list(session.execute(
        select(JobSkillORM.job_id, JobSkillORM.skill_id).where(JobSkillORM.job_id.in_(job_ids))
    ).all())
    skills_by_job: dict[str, set[str]] = {}
    for job_id, skill_id in links:
        skills_by_job.setdefault(job_id, set()).add(skill_id)
    all_skills = {s for skills in skills_by_job.values() for s in skills}
    if not all_skills:
        return {}

    dates = [(as_of - timedelta(days=days - 1 - i)).date() for i in range(days)]
    series: dict[str, dict] = {
        s: {"dates": [d.isoformat() for d in dates], "share": [], "mentions": [], "job_counts": []}
        for s in all_skills
    }
    for day in dates:
        window_start = day - timedelta(days=window_days - 1)
        in_window = [jid for jid, posted in posted_by_job.items()
                     if window_start <= posted.date() <= day]
        job_count = len(in_window)
        counts: dict[str, int] = {}
        for jid in in_window:
            for sid in skills_by_job.get(jid, ()):  # distinct-per-posting
                counts[sid] = counts.get(sid, 0) + 1
        for sid in all_skills:
            mentions = counts.get(sid, 0)
            series[sid]["mentions"].append(float(mentions))
            series[sid]["job_counts"].append(float(job_count))
            series[sid]["share"].append(float(mentions / job_count) if job_count else 0.0)
    return series


def persist_skill_metrics(
    session: Session,
    series: dict[str, dict],
    *,
    as_of: datetime | None = None,
    scope_type: str = "global",
    scope_value: str = "",
    is_demo: bool = False,
) -> int:
    """Write one `skill_metrics` row per (skill, day). Idempotent on the
    natural key, so recomputation overwrites rather than duplicates."""
    as_of = as_of or datetime.now(timezone.utc)
    # Load every existing row for this scope in ONE query and index it by
    # (skill_id, as_of). The natural-key lookup is otherwise a SELECT per row,
    # which is thousands of round-trips for a single recompute.
    existing: dict[tuple[str, datetime], SkillMetricORM] = {
        (row.skill_id, row.as_of): row
        for row in session.scalars(
            select(SkillMetricORM)
            .where(SkillMetricORM.scope_type == scope_type)
            .where(SkillMetricORM.scope_value == scope_value)
        )
    }
    written = 0
    for skill_id, data in series.items():
        shares = data["share"]
        for i, date_str in enumerate(data["dates"]):
            day = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            prefix = shares[: i + 1]
            row = existing.get((skill_id, day))
            values = dict(
                skill_mentions=int(data["mentions"][i]),
                job_count=int(data["job_counts"][i]),
                skill_share=float(shares[i]),
                # Computed on the prefix only -- a metric row must never see
                # data from after its own as_of date, or every backtest built
                # on this table is leaking the future.
                change_7d=pct_change_over(prefix, 7),
                change_30d=pct_change_over(prefix, 30),
                acceleration=accel_fn(prefix, 7),
                zscore=zscore(prefix, 30),
                is_demo=is_demo,
            )
            if row is None:
                session.add(SkillMetricORM(
                    id=str(uuid.uuid4()), skill_id=skill_id, as_of=day,
                    scope_type=scope_type, scope_value=scope_value, **values))
                written += 1
            else:
                for key, value in values.items():
                    setattr(row, key, value)
    session.flush()
    return written


def latest_metrics(session: Session, *, scope_type: str = "global",
                   scope_value: str = "") -> dict[str, SkillMetricORM]:
    """Most recent metric row per skill for the scope."""
    rows = session.scalars(
        select(SkillMetricORM)
        .where(SkillMetricORM.scope_type == scope_type)
        .where(SkillMetricORM.scope_value == scope_value)
        .order_by(SkillMetricORM.as_of)
    ).all()
    out: dict[str, SkillMetricORM] = {}
    for row in rows:
        out[row.skill_id] = row       # ordered ascending, so last wins
    return out


def skill_share_series(session: Session, skill_id: str, *, scope_type: str = "global",
                       scope_value: str = "") -> list[float]:
    rows = session.scalars(
        select(SkillMetricORM)
        .where(SkillMetricORM.skill_id == skill_id)
        .where(SkillMetricORM.scope_type == scope_type)
        .where(SkillMetricORM.scope_value == scope_value)
        .order_by(SkillMetricORM.as_of)
    ).all()
    return [r.skill_share for r in rows]
