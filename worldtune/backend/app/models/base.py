"""Shared SQLAlchemy plumbing for WorldTune's ORM.

Written to run unchanged on SQLite (default, zero-infra) and on
PostgreSQL (docker-compose topology):

  * `UTCDateTime` -- SQLite's DateTime silently drops tzinfo on round-trip,
    which breaks every naive/aware comparison in the trend engine. This
    decorator stores naive-UTC and always hands back tz-aware UTC.
    (Same trick WorldPulse uses; re-implemented here rather than imported,
    to keep the two products decoupled.)
  * `JSONColumn` -- SQLAlchemy's generic `JSON` type maps to TEXT on SQLite
    and to native `json`/`jsonb` on Postgres, so the `metadata` bags in the
    section-18 schema work on both.
  * `EmbeddingColumn` -- a JSON-encoded `list[float]`. On Postgres this
    would instead be declared as `pgvector.sqlalchemy.Vector(128)`; see the
    comment on the type below. This is a *documented simplification*, not a
    fake: the vectors are genuinely computed (app/ranking/embedding.py) and
    genuinely used for cosine similarity, they just aren't ANN-indexed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, TypeDecorator
from sqlalchemy.orm import DeclarativeBase


class UTCDateTime(TypeDecorator):
    """Timezone-safe DateTime for both SQLite and Postgres."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


# Generic JSON: TEXT on SQLite, jsonb-capable on Postgres. Used for the
# `metadata` bags and for list-valued persona fields.
JSONColumn = JSON

# Embedding storage.
#
# SQLite (default here):   JSON-encoded list[float], cosine computed in Python.
# Postgres (docker-compose): swap the line below for
#
#     from pgvector.sqlalchemy import Vector
#     EmbeddingColumn = Vector(128)
#
# ...and the ORM/query code above it is unchanged apart from being able to use
# `ORDER BY embedding <=> :query_vec` for ANN search instead of a Python scan.
EmbeddingColumn = JSON

EMBEDDING_DIM = 128


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for every WorldTune table."""
