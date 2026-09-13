"""Demo-mode seeding (spec section 30).

Populates a working product from empty: persona, 90 days of prices for 8
assets, ~26 news events, 48 jobs with extracted skills, 24 technologies x 8
weekly snapshots, 60 days of skill metrics across three scopes, and a set of
already-resolved historical predictions.

Two requirements this must satisfy, and both are easy to get wrong:

  1. **Trend metrics must be computable on the first run.** Seeding only
     "today" would make every 7d/30d change zero and the whole product look
     broken. So history is seeded, not a snapshot.
  2. **Evaluation must have something to report.** A prediction framework
     with no resolved predictions cannot show accuracy or calibration, so
     historical predictions are generated *and resolved against the seeded
     price history* -- the outcomes are read from the data, not invented.

Every row is tagged `is_demo=True` and every source string is prefixed
`demo:`, so real ingestion can run into the same database later without
ambiguity about what came from where.

Idempotent: re-running updates rather than duplicating (the ingest layer
dedups, and `seed_demo` skips when the DB already holds demo data unless
`force=True`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.trajectory import financial_trajectory
from app.analytics.trend import realized_volatility
from app.models import (
    JobORM,
    MarketAssetORM,
    MarketPriceORM,
    NewsEventORM,
    PredictionORM,
    SkillMetricORM,
    TechnologyEventORM,
)
from app.predictions.store import record_prediction, resolve_prediction
from app.providers.jobs.demo import DemoJobsProvider
from app.providers.market.demo import DEMO_ASSETS, DemoMarketDataProvider
from app.providers.news.demo import DemoNewsProvider
from app.providers.technology.demo import DEMO_TECH_BY_NAME, DemoTechnologyProvider
from app.repositories.ingest import (
    ensure_skills,
    ingest_jobs,
    ingest_news,
    ingest_prices,
    ingest_tech_events,
)
from app.repositories.persona import ensure_demo_persona
from app.skills.metrics import compute_skill_series, persist_skill_metrics

logger = logging.getLogger(__name__)

PRICE_HISTORY_DAYS = 90
SKILL_HISTORY_DAYS = 60

# Scopes seeded so role- and location-specific demand is queryable immediately.
SEED_SCOPES: tuple[tuple[str, str], ...] = (
    ("global", ""),
    ("role_family", "data-engineering"),
    ("role_family", "ai-ml"),
    ("location", "Bengaluru"),
)


def is_seeded(session: Session) -> bool:
    return bool(session.scalar(select(func.count()).select_from(MarketPriceORM)))


def seed_demo(session: Session, *, as_of: datetime | None = None,
              force: bool = False) -> dict:
    """Seed the full demo dataset. Returns per-table counts."""
    as_of = as_of or datetime.now(timezone.utc)
    if is_seeded(session) and not force:
        logger.info("demo data already present; skipping seed")
        return {"skipped": True, **counts(session)}

    persona = ensure_demo_persona(session)
    ensure_skills(session)

    # --- market ---------------------------------------------------------
    market = DemoMarketDataProvider(as_of=as_of)
    sector_by_symbol = {a.symbol: a.sector for a in DEMO_ASSETS}
    prices = market.fetch_prices(market.supported_symbols(), days=PRICE_HISTORY_DAYS)
    ingest_prices(session, prices, is_demo=True, sector_by_symbol=sector_by_symbol)
    for spec in DEMO_ASSETS:
        asset = session.get(MarketAssetORM, spec.symbol)
        if asset is not None:
            asset.name, asset.sector, asset.is_demo = spec.name, spec.sector, True

    # --- news -----------------------------------------------------------
    ingest_news(session, DemoNewsProvider(as_of=as_of).fetch_news(limit=100), is_demo=True)

    # --- jobs -----------------------------------------------------------
    ingest_jobs(session, DemoJobsProvider(as_of=as_of).fetch_jobs(limit=100), is_demo=True)

    # --- technology -----------------------------------------------------
    tech_provider = DemoTechnologyProvider(as_of=as_of)
    ingest_tech_events(
        session,
        tech_provider.fetch_tech_events(limit=0),
        is_demo=True,
        skills_by_name={name: list(spec.related_skills)
                        for name, spec in DEMO_TECH_BY_NAME.items()},
    )

    # --- derived skill metrics -----------------------------------------
    for scope_type, scope_value in SEED_SCOPES:
        series = compute_skill_series(session, as_of=as_of, days=SKILL_HISTORY_DAYS,
                                      scope_type=scope_type, scope_value=scope_value)
        persist_skill_metrics(session, series, as_of=as_of, scope_type=scope_type,
                              scope_value=scope_value, is_demo=True)

    # --- historical predictions + resolutions ---------------------------
    seed_historical_predictions(session, persona_id=persona.id, as_of=as_of)

    session.flush()
    return {"skipped": False, **counts(session)}


def seed_historical_predictions(session: Session, *, persona_id: str,
                                as_of: datetime, horizons: tuple[int, ...] = (7,),
                                lookbacks: tuple[int, ...] = (14, 21, 28, 35, 42, 49, 56)
                                ) -> int:
    """Replay the financial model at past dates and resolve against what the
    seeded price history actually did.

    This is a genuine backtest of the V1 model over the demo series, not a
    table of invented outcomes: at each past date the model sees only the bars
    up to that date, and the outcome is read from the bars after it. The
    accuracy it produces is therefore real -- real *about simulated prices*,
    which is exactly what it claims to be and nothing more.
    """
    assets = list(session.scalars(select(MarketAssetORM)))
    created = 0
    for asset in assets:
        rows = list(session.scalars(
            select(MarketPriceORM)
            .where(MarketPriceORM.asset_id == asset.id)
            .order_by(MarketPriceORM.timestamp)
        ))
        if len(rows) < 60:
            continue
        for horizon in horizons:
            for lookback in lookbacks:
                cutoff = as_of - timedelta(days=lookback)
                history = [r for r in rows if r.timestamp <= cutoff]
                future = [r for r in rows if r.timestamp > cutoff]
                if len(history) < 25 or not future:
                    continue
                traj = financial_trajectory(
                    [r.close for r in history], [r.volume for r in history],
                    horizon_days=horizon,
                )
                prediction = record_prediction(
                    session,
                    persona_id=persona_id, domain="financial", entity_type="asset",
                    entity_id=asset.id, predicted_direction=traj.direction,
                    predicted_probability=traj.probability, confidence=traj.confidence,
                    horizon_days=horizon, features=traj.features,
                    rationale=traj.rationale, created_at=cutoff, is_demo=True,
                )
                created += 1

                target_time = cutoff + timedelta(days=horizon)
                # Nearest bar at or after the horizon; skip if the horizon
                # extends past the seeded history.
                resolved_bar = next((r for r in future if r.timestamp >= target_time), None)
                if resolved_bar is None:
                    continue
                start_close = history[-1].close
                realized = (resolved_bar.close / start_close - 1.0) if start_close else 0.0
                outcome = grade_outcome(realized, [r.close for r in history],
                                        horizon_days=horizon)
                resolve_prediction(
                    session, prediction, actual_outcome=outcome,
                    actual_value=round(realized, 6), resolved_at=resolved_bar.timestamp,
                    notes=f"{horizon}d realized return {realized:+.2%} on seeded history",
                    is_demo=True,
                )
    session.flush()
    return created


def grade_outcome(realized_return: float, history_closes: list[float], *,
                  horizon_days: int, band_fraction: float = 0.5) -> str:
    """Grade a realized return as bullish / neutral / bearish.

    The neutral band is **scaled to the asset's own volatility**, not fixed.
    A fixed +/-1% band is the obvious implementation and it is wrong: BTC at
    ~3% daily volatility has a ~8% one-week standard deviation, so a 1% band
    catches almost nothing and grades essentially every outcome as
    directional -- while the model, whose neutral band lives in probability
    space, calls neutral roughly half the time. Those two bands then disagree
    by construction and the measured accuracy reflects the mismatch rather
    than the model.

    Scaling by `band_fraction` x sigma x sqrt(horizon) makes "no meaningful
    move" mean the same thing on both sides of the comparison, and makes it
    asset-relative: 2% is a big week for QQQ and a quiet one for BTC.
    """
    sigma_annual = realized_volatility(history_closes)
    sigma_horizon = sigma_annual * (horizon_days / 365.0) ** 0.5
    # Floor the band so a degenerate (near-zero-volatility) history cannot
    # collapse it to zero and grade rounding noise as a directional move.
    threshold = max(0.005, band_fraction * sigma_horizon)
    if realized_return > threshold:
        return "bullish"
    if realized_return < -threshold:
        return "bearish"
    return "neutral"


def counts(session: Session) -> dict:
    def n(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "market_assets": n(MarketAssetORM),
        "market_prices": n(MarketPriceORM),
        "news_events": n(NewsEventORM),
        "jobs": n(JobORM),
        "technology_events": n(TechnologyEventORM),
        "skill_metrics": n(SkillMetricORM),
        "predictions": n(PredictionORM),
    }
