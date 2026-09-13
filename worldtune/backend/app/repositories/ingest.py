"""Persist canonical provider output into the ORM.

Every function here is idempotent: re-running ingestion over an overlapping
window updates rather than duplicates. Idempotency is what makes a scheduled
refresh safe, and it is enforced by the dedup hashes in
`app.repositories.dedup` plus natural keys (asset+timestamp for prices).

Each ingester also writes a generic `SignalORM` row, so the ranking layer has
one uniform surface to read (see app/models/signals.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.graph import get_entity_graph
from app.models import (
    JobORM,
    JobSkillORM,
    MarketAssetORM,
    MarketPriceORM,
    NewsEventORM,
    SignalORM,
    SkillORM,
    TechnologyEventORM,
)
from app.providers.jobs.classify import classify_role_family, classify_seniority
from app.ranking.embedding import embed_text
from app.repositories.dedup import job_hash, news_hash, tech_hash
from app.schemas.canonical import (
    CanonicalJob,
    CanonicalMarketPrice,
    CanonicalNewsEvent,
    CanonicalTechEvent,
)
from app.skills.extraction import extract_skills
from app.skills.taxonomy import SKILLS


# --- skills ------------------------------------------------------------------

def ensure_skills(session: Session) -> None:
    """Materialize the taxonomy into the `skills` table. Idempotent."""
    existing = {s for s in session.scalars(select(SkillORM.id)).all()}
    for spec in SKILLS:
        if spec.id in existing:
            continue
        session.add(SkillORM(id=spec.id, name=spec.name, category=spec.category,
                             aliases=list(spec.aliases)))
    session.flush()


# --- market ------------------------------------------------------------------

def ensure_asset(session: Session, *, symbol: str, asset_class: str, name: str = "",
                 sector: str = "", is_demo: bool = False) -> MarketAssetORM:
    row = session.get(MarketAssetORM, symbol)
    if row is None:
        row = MarketAssetORM(id=symbol, symbol=symbol, name=name or symbol,
                             asset_class=asset_class, sector=sector, is_demo=is_demo)
        session.add(row)
        session.flush()
    else:
        # Backfill metadata that a later, richer provider supplies.
        if name and not row.name:
            row.name = name
        if sector and not row.sector:
            row.sector = sector
    return row


def ingest_prices(session: Session, prices: list[CanonicalMarketPrice], *,
                  is_demo: bool = False, sector_by_symbol: dict[str, str] | None = None) -> int:
    """Upsert OHLCV bars on (asset_id, timestamp). Returns rows written."""
    sector_by_symbol = sector_by_symbol or {}
    written = 0
    for price in prices:
        ensure_asset(session, symbol=price.symbol, asset_class=price.asset_class,
                     sector=sector_by_symbol.get(price.symbol, ""), is_demo=is_demo)
        ts = _as_utc(price.timestamp)
        existing = session.scalar(
            select(MarketPriceORM)
            .where(MarketPriceORM.asset_id == price.symbol)
            .where(MarketPriceORM.timestamp == ts)
        )
        if existing is None:
            session.add(MarketPriceORM(
                id=str(uuid.uuid4()), asset_id=price.symbol, timestamp=ts,
                open=price.open, high=price.high, low=price.low, close=price.close,
                volume=price.volume, source=price.source, is_demo=is_demo,
            ))
            written += 1
        else:
            # A revised bar (late volume, corrected close) replaces the old one.
            existing.open, existing.high = price.open, price.high
            existing.low, existing.close = price.low, price.close
            existing.volume, existing.source = price.volume, price.source
    session.flush()
    return written


# --- news --------------------------------------------------------------------

def ingest_news(session: Session, events: list[CanonicalNewsEvent], *,
                is_demo: bool = False) -> int:
    written = 0
    for event in events:
        digest = news_hash(event.title)
        if not digest:
            continue
        if session.scalar(select(NewsEventORM).where(NewsEventORM.dedup_hash == digest)):
            continue
        event_id = str(uuid.uuid4())
        published = _as_utc(event.published_at)
        session.add(NewsEventORM(
            id=event_id, published_at=published, ingested_at=datetime.now(timezone.utc),
            title=event.title, summary=event.summary, url=event.url, source=event.source,
            domain=event.domain, language=event.language, sentiment=event.sentiment,
            entities=event.entities, sectors=event.sectors, tickers=event.tickers,
            dedup_hash=digest, is_demo=is_demo,
        ))
        # One generic signal per resolved ticker (so per-asset news lookups are
        # an indexed query), or one topical signal when no ticker resolved.
        targets = event.tickers or [event.sectors[0] if event.sectors else "technology"]
        for target in targets:
            session.add(SignalORM(
                id=str(uuid.uuid4()), signal_type="news",
                entity_type="asset" if target in event.tickers else "topic",
                entity_id=target, timestamp=published, title=event.title,
                description=event.summary, source=event.source,
                raw_score=1.0, sentiment=event.sentiment,
                meta={"url": event.url, "domain": event.domain,
                      "entities": event.entities, "news_id": event_id},
                embedding=embed_text(f"{event.title} {' '.join(event.entities)}"),
                is_demo=is_demo,
            ))
        written += 1
    session.flush()
    return written


# --- jobs --------------------------------------------------------------------

def ingest_jobs(session: Session, jobs: list[CanonicalJob], *, is_demo: bool = False) -> int:
    ensure_skills(session)
    written = 0
    for job in jobs:
        digest = job_hash(job.title, job.company, job.location)
        if not digest:
            continue
        if session.scalar(select(JobORM).where(JobORM.dedup_hash == digest)):
            continue
        job_id = str(uuid.uuid4())
        posted = _as_utc(job.posted_at)
        session.add(JobORM(
            id=job_id, external_id=job.external_id, title=job.title, company=job.company,
            description=job.description, location=job.location, country=job.country,
            remote=job.remote,
            seniority=classify_seniority(job.title),
            role_family=classify_role_family(job.title, job.description),
            salary_min=job.salary_min, salary_max=job.salary_max,
            salary_currency=job.salary_currency, url=job.url, source=job.source,
            posted_at=posted, ingested_at=datetime.now(timezone.utc),
            dedup_hash=digest, is_demo=is_demo,
        ))
        # Title is scanned alongside the body: "Senior Spark Engineer" states a
        # skill the prose sometimes assumes.
        for skill_id, mentions in extract_skills(f"{job.title}\n{job.description}").items():
            session.add(JobSkillORM(id=str(uuid.uuid4()), job_id=job_id,
                                    skill_id=skill_id, mentions=int(mentions)))
        session.add(SignalORM(
            id=str(uuid.uuid4()), signal_type="job", entity_type="role",
            entity_id=classify_role_family(job.title, job.description),
            timestamp=posted, title=job.title, description=f"{job.company} - {job.location}",
            source=job.source, raw_score=1.0, sentiment=0.0,
            meta={"job_id": job_id, "url": job.url, "location": job.location,
                  "seniority": classify_seniority(job.title), "remote": job.remote},
            embedding=embed_text(f"{job.title} {job.description[:1000]}"),
            is_demo=is_demo,
        ))
        written += 1
    session.flush()
    return written


# --- technology --------------------------------------------------------------

def ingest_tech_events(session: Session, events: list[CanonicalTechEvent], *,
                       is_demo: bool = False,
                       skills_by_name: dict[str, list[str]] | None = None) -> int:
    graph = get_entity_graph()
    skills_by_name = skills_by_name or {}
    written = 0
    for event in events:
        observed = _as_utc(event.observed_at)
        # Snapshots of the same technology on different days are DIFFERENT
        # observations -- the whole point is the series -- so the date is part
        # of the identity.
        digest = tech_hash(event.name, f"{event.title}|{observed.date().isoformat()}")
        if session.scalar(select(TechnologyEventORM).where(
                TechnologyEventORM.dedup_hash == digest)):
            continue
        related = skills_by_name.get(event.name) or _infer_skills(event, graph)
        tech_id = str(uuid.uuid4())
        session.add(TechnologyEventORM(
            id=tech_id, observed_at=observed, name=event.name, category=event.category,
            title=event.title, url=event.url, source=event.source, stars=event.stars,
            stars_7d_delta=event.stars_7d_delta, points=event.points,
            mentions=event.mentions, related_skills=related, dedup_hash=digest,
            is_demo=is_demo,
        ))
        session.add(SignalORM(
            id=str(uuid.uuid4()), signal_type="technology", entity_type="topic",
            entity_id=event.name, timestamp=observed, title=event.title or event.name,
            description=event.category, source=event.source,
            raw_score=float(event.stars_7d_delta or event.points or 0.0), sentiment=0.0,
            meta={"tech_id": tech_id, "url": event.url, "stars": event.stars,
                  "related_skills": related},
            embedding=embed_text(f"{event.name} {event.title} {event.category}"),
            is_demo=is_demo,
        ))
        written += 1
    session.flush()
    return written


def _infer_skills(event: CanonicalTechEvent, graph) -> list[str]:
    """Map a technology to taxonomy skills by scanning its name and headline."""
    from app.skills.extraction import extract_skill_ids

    return extract_skill_ids(f"{event.name} {event.title} {event.category}")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None \
        else value.astimezone(timezone.utc)
