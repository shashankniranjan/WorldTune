"""FastAPI app factory / entrypoint.

    uvicorn app.main:app --reload

Startup behaviour is the product's core promise: with no .env, no API keys
and no external services, `init_db()` creates the SQLite schema and
`seed_demo()` fills it, so the very first request to /api/dashboard returns a
populated, fully-explained response. Seeding is skipped when data already
exists, so a restart is cheap and a real-ingestion database is never
overwritten.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.security import RateLimitMiddleware, TimeoutMiddleware
from app.config import settings
from app.db import init_db, session_scope
from app.seed.demo import seed_demo
from app.services.world_shift_refresh import refresh_service
from app.services.world_shift_runtime import get_runtime_values

logger = logging.getLogger(__name__)


async def _scheduled_world_shift_refresh() -> None:
    """Queue background snapshot refreshes while reads keep serving ACTIVE data."""
    await asyncio.sleep(max(0, settings.world_shift_refresh_startup_delay_seconds))
    while True:
        try:
            run = await asyncio.to_thread(refresh_service.request_refresh)
            logger.info("World Shift scheduled refresh: run=%s status=%s", run.run_id, run.status)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("World Shift scheduled refresh could not be queued")
        interval, _, _ = await asyncio.to_thread(get_runtime_values)
        # Re-read persisted UI configuration at least once per minute so a
        # switch from 12 hours back to 5 minutes takes effect promptly.
        remaining = max(300, interval)
        while remaining > 0:
            step = min(60, remaining)
            await asyncio.sleep(step)
            remaining -= step
            latest_interval, _, _ = await asyncio.to_thread(get_runtime_values)
            if latest_interval < interval:
                remaining = min(remaining, latest_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed:
        try:
            with session_scope() as session:
                result = seed_demo(session)
            logger.info("WorldTune startup seed: %s", result)
        except Exception:
            # A seeding failure must not prevent the API from serving; the
            # endpoints degrade to "no data" rather than to "no service".
            logger.exception("demo seeding failed at startup; continuing without it")
    refresh_task = None
    if settings.world_shift_auto_refresh_enabled:
        refresh_task = asyncio.create_task(_scheduled_world_shift_refresh())
    try:
        yield
    finally:
        if refresh_task:
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="WorldTune API",
        description=(
            "Persona-driven personalization layer: Financial Pulse and Career Pulse. "
            "Research prototype -- no profitability claim, not investment or career advice."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    # Order matters: timeout is added last so it wraps the rate limiter and
    # bounds the whole chain.
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
