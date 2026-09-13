"""Engine / session management.

`DATABASE_URL` defaults to SQLite so tests and the demo need zero external
services; docker-compose points it at Postgres+pgvector. The only
dialect-specific concession is the SQLite `check_same_thread` flag needed by
FastAPI's threadpool.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine(url: str | None = None) -> Engine:
    global _engine, _SessionFactory
    target = url or settings.database_url
    if _engine is None or str(_engine.url) != target:
        kwargs: dict = {"future": True}
        if target.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(target, **kwargs)
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    get_engine()
    assert _SessionFactory is not None
    return _SessionFactory


def init_db(url: str | None = None) -> Engine:
    """Create every table. Idempotent -- safe to call on each boot."""
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


def reset_engine() -> None:
    """Drop cached engine/session factory (tests swap DATABASE_URL per case)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
