"""Database settings and connection configuration."""

import os


class DatabaseSettings:
    """Load database connection settings from environment variables."""

    def __init__(self) -> None:
        url = os.environ.get("HARVESTER_DATABASE_URL")
        if not url:
            raise ValueError(
                "HARVESTER_DATABASE_URL environment variable is required. "
                "Set it to a PostgreSQL connection string like "
                "postgresql+psycopg://user:pass@host:port/dbname"
            )
        self._database_url = url

    @property
    def database_url(self) -> str:
        """Synchronous database URL (psycopg driver)."""
        return self._database_url

    @property
    def async_database_url(self) -> str:
        """Async database URL (asyncpg driver) for async SQLAlchemy engine."""
        return self._database_url.replace("+psycopg", "+asyncpg", 1)
