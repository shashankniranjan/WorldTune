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

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.security import RateLimitMiddleware, TimeoutMiddleware
from app.config import settings
from app.db import init_db, session_scope
from app.seed.demo import seed_demo

logger = logging.getLogger(__name__)


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
    yield


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
