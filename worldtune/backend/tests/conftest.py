"""Shared fixtures.

Each test gets its own file-backed SQLite database in a tmp_path. File-backed
rather than `:memory:` because the app obtains sessions from a module-level
factory and FastAPI's TestClient runs handlers on a threadpool -- an
in-memory SQLite database is per-connection and would appear empty to the
handler thread.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app import config as config_module
from app.db import init_db, reset_engine, session_scope

# A fixed clock, so every seeded series and every assertion about "7 days ago"
# is reproducible regardless of when the suite runs.
FIXED_NOW = datetime(2025, 9, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(config_module.settings, "demo_mode", True)
    monkeypatch.setattr(config_module.settings, "auto_seed", False)
    monkeypatch.setattr(config_module.settings, "llm_api_key", None)
    monkeypatch.setattr(config_module.settings, "adzuna_app_id", None)
    monkeypatch.setattr(config_module.settings, "adzuna_app_key", None)
    return config_module.settings


@pytest.fixture
def db(tmp_path, settings, monkeypatch):
    url = f"sqlite:///{tmp_path}/worldtune_test.db"
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine()
    init_db(url)
    yield url
    reset_engine()


@pytest.fixture
def session(db):
    with session_scope() as s:
        yield s


@pytest.fixture
def seeded(db):
    """A database with the full demo dataset anchored at the real current time.

    Deliberately NOT anchored to FIXED_NOW: the services and API endpoints
    read the wall clock for their own `as_of`, so a fixture frozen in the
    past would place every seeded row outside the endpoints' recency windows
    and the suite would assert against an empty product. Determinism still
    holds where it matters -- the demo generators are seeded, so the *shape*
    of every series is identical run to run; only the absolute dates move.
    Tests that need an exact clock pass `as_of` explicitly.
    """
    from app.seed.demo import seed_demo

    with session_scope() as s:
        seed_demo(s, as_of=datetime.now(timezone.utc))
    return db


@pytest.fixture
def persona(seeded):
    from app.repositories.persona import get_persona

    with session_scope() as s:
        return get_persona(s)


@pytest.fixture
def client(seeded):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def empty_client(db):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c
