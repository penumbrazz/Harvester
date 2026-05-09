"""Tests for failure inspection API endpoint."""

import os
import uuid
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for API tests."""
    db_name = f"harvester_fail_test_{uuid.uuid4().hex[:8]}"
    admin_url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    test_url = admin_url.rsplit("/", 1)[0] + "/" + db_name

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    if env_backup:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    yield test_url

    admin_engine2 = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine2.connect() as conn:
        conn.execute(
            text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}'"
            )
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    admin_engine2.dispose()


@pytest.fixture()
async def api_client(api_test_db):
    """Create an async API test client with database configured."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": api_test_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_get_recent_failures_returns_empty(api_client):
    """GET /failures/recent should return empty lists when no failures exist."""
    # Act
    resp = await api_client.get(
        "/failures/recent",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "crawl_runs" in data
    assert "jobs" in data
    assert data["crawl_runs"] == []
    assert data["jobs"] == []


@pytest.mark.asyncio
async def test_get_recent_failures_with_limit(api_client):
    """GET /failures/recent?limit=5 should accept the limit parameter."""
    # Act
    resp = await api_client.get(
        "/failures/recent?limit=5",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
