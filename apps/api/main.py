"""FastAPI app factory / entrypoint.

Run with: uvicorn apps.api.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI

from worldpulse.api.routes import router as worldpulse_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="WorldPulse API",
        description="Event-driven market impact prediction prototype.",
        version="0.1.0",
    )
    app.include_router(worldpulse_router)
    return app


app = create_app()
