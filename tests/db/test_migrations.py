"""Tests for Alembic migration against an isolated Postgres database."""

import os

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _alembic_cfg(test_db_url: str) -> Config:
    """Create Alembic config pointing at the test database."""
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    return cfg


def test_alembic_version_recorded(_test_db_engine):
    """Migration should record version in alembic_version table."""
    with _test_db_engine.connect() as conn:
        result = conn.execute(sa.text("SELECT version_num FROM alembic_version"))
        versions = result.fetchall()
        assert len(versions) >= 1, "At least one migration should be recorded"


def test_alembic_downgrade_base(_test_db_url, _test_db_engine, _test_db_name):
    """Alembic should downgrade from head to base without errors."""
    # Unset env var to prevent env.py override
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = _alembic_cfg(_test_db_url)
    command.downgrade(cfg, "base")
    if env_backup is not None:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    with _test_db_engine.connect() as conn:
        result = conn.execute(
            sa.text(
                "SELECT relname FROM pg_class "
                "WHERE relkind='r' AND relnamespace = "
                "(SELECT oid FROM pg_namespace WHERE nspname = 'public') "
                "AND relname != 'alembic_version'"
            )
        )
        tables = result.fetchall()
        assert len(tables) == 0, f"Expected no user tables after downgrade, got {tables}"

    # Re-upgrade for other tests in the session
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    command.upgrade(_alembic_cfg(_test_db_url), "head")
    if env_backup is not None:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup
