"""Shared FastAPI dependency providers for Harvester."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Cached engine metadata — lazily initialised on first request and reused
# until HARVESTER_DATABASE_URL changes (e.g. in test fixtures).
_cached_url: str | None = None
_engine: object | None = None  # actual type: sqlalchemy.engine.Engine


def _get_engine() -> object:
    """Return a cached :class:`Engine`, creating a new one when the URL changes.

    In production the URL is stable so the same engine is reused across all
    requests.  In tests that ``patch.dict(os.environ, ...)`` the URL, a fresh
    engine is created automatically.
    """
    global _cached_url, _engine

    current_url = os.environ.get("HARVESTER_DATABASE_URL")
    if current_url != _cached_url or _engine is None:
        if _engine is not None:
            _engine.dispose()
        if not current_url:
            raise ValueError(
                "HARVESTER_DATABASE_URL environment variable is required. "
                "Set it to a PostgreSQL connection string like "
                "postgresql+psycopg://user:pass@host:port/dbname"
            )
        _engine = create_engine(current_url)
        _cached_url = current_url

    return _engine


def get_db_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy :class:`Session` from the shared engine pool.

    Reads ``HARVESTER_DATABASE_URL`` from the environment on each call so that
    test fixtures which patch the env-var get a fresh engine.  When the URL has
    not changed the previously created engine is reused.

    Yields
    ------
    Session
        A database session scoped to the current HTTP request.
    """
    engine = _get_engine()
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
