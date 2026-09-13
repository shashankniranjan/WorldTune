"""Career Pulse tables: `jobs`, `skills`, `job_skills`, `skill_metrics`.

`job_skills` is the association row produced by deterministic keyword/phrase
extraction over the job description (app/skills/extraction.py) -- no LLM is
involved in extraction, so the counts underneath every skill metric are
reproducible and auditable.

`skill_metrics` is a *time series*, one row per (skill, as_of_date, scope).
That is what makes 7d/30d change and acceleration real computations rather
than stored constants: the seeder writes ~60 days of history so the trend
engine has something to differentiate on the very first run.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONColumn, UTCDateTime, utcnow


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, index=True, default="")
    title: Mapped[str] = mapped_column(String, index=True)
    company: Mapped[str] = mapped_column(String, default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String, default="", index=True)
    country: Mapped[str] = mapped_column(String, default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    seniority: Mapped[str] = mapped_column(String, default="", index=True)  # junior|mid|senior|staff|principal
    role_family: Mapped[str] = mapped_column(String, default="", index=True)  # data-engineering|ai-ml|platform
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, index=True)
    posted_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    dedup_hash: Mapped[str] = mapped_column(String, index=True, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (Index("ix_jobs_posted_family", "posted_at", "role_family"),)


class SkillORM(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)   # canonical slug, e.g. "spark"
    name: Mapped[str] = mapped_column(String, index=True)       # "Spark"
    category: Mapped[str] = mapped_column(String, index=True)   # data-engineering|ai-ml|cloud
    aliases: Mapped[list] = mapped_column(JSONColumn, default=list)


class JobSkillORM(Base):
    __tablename__ = "job_skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), index=True)
    mentions: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)


class SkillMetricORM(Base):
    """One row per (skill, as_of, scope). Scope narrows the denominator so the
    spec's "role- and location-specific demand" is a query, not a special case:
      scope_type in {global, role_family, location}
      scope_value e.g. "data-engineering" / "Bengaluru" / "" for global
    """

    __tablename__ = "skill_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), index=True)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    scope_type: Mapped[str] = mapped_column(String, default="global", index=True)
    scope_value: Mapped[str] = mapped_column(String, default="", index=True)

    skill_mentions: Mapped[int] = mapped_column(Integer, default=0)
    job_count: Mapped[int] = mapped_column(Integer, default=0)   # jobs in scope on that day
    skill_share: Mapped[float] = mapped_column(Float, default=0.0)  # mentions / job_count
    change_7d: Mapped[float] = mapped_column(Float, default=0.0)    # fractional change
    change_30d: Mapped[float] = mapped_column(Float, default=0.0)
    acceleration: Mapped[float] = mapped_column(Float, default=0.0)
    zscore: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        UniqueConstraint("skill_id", "as_of", "scope_type", "scope_value", name="uq_skill_metric"),
        Index("ix_skill_metrics_skill_asof", "skill_id", "as_of"),
    )
