from __future__ import annotations

import pytest

from worldpulse.database.repository import init_db, make_engine, make_session_factory


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite session for each test."""
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
