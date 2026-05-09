"""Tests for database settings loading."""

import os
from unittest.mock import patch

import pytest


def test_settings_read_database_url_from_env():
    """Settings should read HARVESTER_DATABASE_URL from environment."""
    from harvester.db.settings import DatabaseSettings

    url = "postgresql+psycopg://user:pass@localhost:5432/testdb"
    with patch.dict(os.environ, {"HARVESTER_DATABASE_URL": url}):
        settings = DatabaseSettings()
        assert settings.database_url == url


def test_settings_missing_database_url_raises():
    """Settings should raise a clear error when HARVESTER_DATABASE_URL is missing."""
    from harvester.db.settings import DatabaseSettings

    with patch.dict(os.environ, {}, clear=True):
        # Remove the key if it exists
        os.environ.pop("HARVESTER_DATABASE_URL", None)
        with pytest.raises(ValueError, match="HARVESTER_DATABASE_URL"):
            DatabaseSettings()


def test_settings_exposes_async_url():
    """Settings should expose an async-compatible URL for SQLAlchemy async engine."""
    from harvester.db.settings import DatabaseSettings

    url = "postgresql+psycopg://user:pass@localhost:5432/testdb"
    with patch.dict(os.environ, {"HARVESTER_DATABASE_URL": url}):
        settings = DatabaseSettings()
        assert settings.async_database_url == url.replace("+psycopg", "+asyncpg", 1)
