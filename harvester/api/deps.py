"""Shared FastAPI dependency providers for Harvester."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from harvester.db.settings import DatabaseSettings


def get_db_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy :class:`Session` bound to the configured database.

    Uses the ``HARVESTER_DATABASE_URL`` environment variable (via
    :class:`~harvester.db.settings.DatabaseSettings`) to create a synchronous
    engine.  The session is yielded within a ``try / finally`` block so it is
    always closed after the request completes.

    Yields
    ------
    Session
        A database session scoped to the current HTTP request.
    """
    settings = DatabaseSettings()
    engine = create_engine(settings.database_url)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
