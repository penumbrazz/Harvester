"""Shared database fixtures for schema and migration tests."""

import os
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def _get_test_db_url() -> str:
    """Get the base database URL for test databases."""
    url = os.environ.get("HARVESTER_DATABASE_URL", "")
    if not url:
        url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    return url


def _get_admin_url() -> str:
    """Get admin connection URL (connects to 'postgres' db)."""
    url = _get_test_db_url()
    parts = url.rsplit("/", 1)
    return parts[0] + "/postgres"


@pytest.fixture(scope="session")
def _test_db_name():
    """Generate a unique test database name."""
    return f"harvester_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def _test_db_url(_test_db_name):
    """Get the full URL for the test database."""
    return _get_test_db_url().rsplit("/", 1)[0] + f"/{_test_db_name}"


@pytest.fixture(scope="session")
def _test_db_engine(_test_db_name, _test_db_url):
    """Create an isolated test database for the session, then run migrations."""
    admin_url = _get_admin_url()
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{_test_db_name}"'))

    admin_engine.dispose()

    # Run Alembic migrations BEFORE creating the test engine
    # Unset HARVESTER_DATABASE_URL so env.py doesn't override our test URL
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", _test_db_url)
    command.upgrade(cfg, "head")
    if env_backup is not None:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    # Create engine after migration to ensure connections see migrated schema
    test_engine = create_engine(_test_db_url)

    yield test_engine

    test_engine.dispose()

    with admin_engine.connect() as conn:
        conn.execute(
            sa.text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{_test_db_name}'"
            )
        )
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{_test_db_name}"'))

    admin_engine.dispose()


@pytest.fixture()
def db_connection(_test_db_engine):
    """Provide a database connection with transaction rollback."""
    conn = _test_db_engine.connect()
    transaction = conn.begin()
    yield conn
    transaction.rollback()
    conn.close()
