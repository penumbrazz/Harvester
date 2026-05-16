"""Tests for queue status CLI command and API endpoint.

Verifies that queue status aggregates by job_type and status,
and does NOT return raw payload data.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from typer.testing import CliRunner


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for queue status tests."""
    db_name = f"harvester_queue_test_{uuid.uuid4().hex[:8]}"
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
    """Create an async API test client."""
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


def _insert_job(db_url: str, job_type: str, status: str = "pending") -> str:
    """Insert a job row and return its id."""
    engine = create_engine(db_url)
    jid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO jobs "
                "(id, job_type, status, priority, attempts, max_attempts, "
                "payload, created_at, updated_at) "
                "VALUES (:id, :type, :status, 0, 0, 3, :payload, :ts, :ts)"
            ),
            {
                "id": jid,
                "type": job_type,
                "status": status,
                "payload": '{"secret": "data"}',
                "ts": now,
            },
        )
        conn.commit()
    engine.dispose()
    return str(jid)


@pytest.mark.asyncio
async def test_queue_status_api_returns_aggregation(api_client, api_test_db):
    """GET /queue/status should return counts by job_type and status."""
    _insert_job(api_test_db, "embed_chunks", "pending")
    _insert_job(api_test_db, "embed_chunks", "pending")
    _insert_job(api_test_db, "crawl", "running")

    resp = await api_client.get(
        "/queue/status",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Should have aggregations
    found_embed = any(
        item["job_type"] == "embed_chunks" and item["status"] == "pending"
        for item in data
    )
    assert found_embed


@pytest.mark.asyncio
async def test_queue_status_api_no_payload(api_client, api_test_db):
    """GET /queue/status should NOT return raw payload."""
    _insert_job(api_test_db, "embed_chunks", "pending")

    resp = await api_client.get(
        "/queue/status",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Each item should have job_type, status, count but NOT payload
    for item in data:
        assert "job_type" in item
        assert "status" in item
        assert "count" in item
        assert "payload" not in item


@pytest.mark.asyncio
async def test_queue_status_api_auth_required(api_client, api_test_db):
    """GET /queue/status requires API token."""
    resp = await api_client.get("/queue/status")
    assert resp.status_code == 401


class TestQueueStatusCLI:
    """Tests for queue status CLI command."""

    def test_queue_status_cli_output(self, db_session):
        """queue status should output job_type, status, count."""
        from harvester.cli.main import app

        runner = CliRunner()

        # Insert a job via raw SQL
        jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        db_session.execute(
            text(
                "INSERT INTO jobs "
                "(id, job_type, status, priority, attempts, max_attempts, "
                "created_at, updated_at) "
                "VALUES (:id, 'embed_chunks', 'pending', 0, 0, 3, :ts, :ts)"
            ),
            {"id": jid, "ts": now},
        )
        db_session.commit()

        with patch("harvester.workers.daemon._make_session", return_value=db_session):
            result = runner.invoke(app, ["queue", "status"])

        assert result.exit_code == 0
        assert "embed_chunks" in result.output

    def test_queue_status_cli_empty(self, db_session):
        """queue status with no jobs should show empty message."""
        from harvester.cli.main import app

        runner = CliRunner()

        with patch("harvester.workers.daemon._make_session", return_value=db_session):
            result = runner.invoke(app, ["queue", "status"])

        assert result.exit_code == 0
