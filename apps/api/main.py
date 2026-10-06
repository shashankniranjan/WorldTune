"""FastAPI app factory / entrypoint.

Run with: uvicorn apps.api.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI

from worldtune.api.routes import router as worldtune_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="WorldTune API",
        description="Event-driven market impact prediction prototype.",
        version="0.1.0",
    )
    app.include_router(worldtune_router)
    return app


app = create_app()
