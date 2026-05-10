"""Tests for dashboard summary API endpoint.

Covers: key counts, no raw payload, authentication.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for dashboard API tests."""
    db_name = f"harvester_dash_test_{uuid.uuid4().hex[:8]}"
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
async def test_dashboard_requires_auth(api_client):
    """GET /dashboard/summary should require API token."""
    resp = await api_client.get("/dashboard/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_returns_counts(api_client, api_test_db):
    """GET /dashboard/summary should return key counts."""
    # Insert a source and a crawl run to verify counts
    engine = create_engine(api_test_db)
    now = datetime.now(timezone.utc)
    source_id = uuid.uuid4()
    with Session(bind=engine) as session:
        session.execute(
            sa.text(
                "INSERT INTO sources "
                "(id, name, kind, url, status, trust_level, auth_required, failure_count, "
                "created_at, updated_at) VALUES "
                "(:id, :name, :kind, :url, :status, :trust_level, :auth_required, "
                ":failure_count, :created_at, :updated_at)"
            ),
            dict(
                id=source_id,
                name="dash-test-source",
                kind="web",
                url="https://example.com",
                status="watched",
                trust_level="medium",
                auth_required=False,
                failure_count=0,
                created_at=now,
                updated_at=now,
            ),
        )
        session.execute(
            sa.text(
                "INSERT INTO crawl_runs "
                "(id, source_id, status, started_at, completed_at, created_at) "
                "VALUES (:id, :source_id, 'completed', :started, :completed, :created)"
            ),
            dict(
                id=uuid.uuid4(),
                source_id=source_id,
                started=now,
                completed=now,
                created=now,
            ),
        )
        session.execute(
            sa.text(
                "INSERT INTO jobs "
                "(id, job_type, status, priority, attempts, max_attempts, created_at, updated_at) "
                "VALUES (:id, :job_type, 'pending', 0, 0, 3, :ts, :ts)"
            ),
            dict(
                id=uuid.uuid4(),
                job_type="crawl",
                ts=now,
            ),
        )
        session.commit()
    engine.dispose()

    resp = await api_client.get(
        "/dashboard/summary",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert "crawl_runs" in data
    assert "jobs" in data
    assert "content_items" in data
    assert "failures" in data
    assert "audit_events" in data
    assert data["sources"]["total"] >= 1
    assert data["crawl_runs"]["total"] >= 1
    assert data["jobs"]["total"] >= 1


@pytest.mark.asyncio
async def test_dashboard_summary_no_raw_payload(api_client, api_test_db):
    """GET /dashboard/summary must not include raw HTML/API payload."""
    resp = await api_client.get(
        "/dashboard/summary",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    # Ensure no raw payload fields appear in the response
    body_str = str(data)
    assert "payload" not in body_str.lower() or "payload_count" in body_str.lower()
