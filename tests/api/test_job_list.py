"""Tests for job list API endpoint.

Covers: job_type, status, lane, source filters, attempts/lock fields.
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
    """Create an isolated test database for job list API tests."""
    db_name = f"harvester_job_list_{uuid.uuid4().hex[:8]}"
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


def _insert_job(
    db_url: str,
    *,
    job_type="crawl",
    status="pending",
    lane=None,
    source_id=None,
    attempts=0,
    locked_by=None,
    last_error=None,
):
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with Session(bind=create_engine(db_url)) as session:
        session.execute(
            sa.text(
                "INSERT INTO jobs "
                "(id, job_type, status, priority, attempts, max_attempts, "
                "lane, source_id, locked_by, last_error, created_at, updated_at) "
                "VALUES (:id, :job_type, :status, 0, :attempts, 3, "
                ":lane, :source_id, :locked_by, :last_error, :ts, :ts)"
            ),
            dict(
                id=job_id,
                job_type=job_type,
                status=status,
                attempts=attempts,
                lane=lane,
                source_id=source_id,
                locked_by=locked_by,
                last_error=last_error,
                ts=now,
            ),
        )
        session.commit()
    return job_id


@pytest.mark.asyncio
async def test_jobs_requires_auth(api_client):
    """GET /queue/jobs should require API token."""
    resp = await api_client.get("/queue/jobs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jobs_returns_empty(api_client):
    """GET /queue/jobs should return empty list when no jobs exist."""
    resp = await api_client.get(
        "/queue/jobs",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_jobs_returns_items(api_client, api_test_db):
    """GET /queue/jobs should return job records."""
    _insert_job(api_test_db)

    resp = await api_client.get(
        "/queue/jobs",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "id" in item
    assert "job_type" in item
    assert "status" in item
    assert "attempts" in item
    assert "created_at" in item


@pytest.mark.asyncio
async def test_jobs_filter_by_status(api_client, api_test_db):
    """GET /queue/jobs?status=failed should filter by status."""
    _insert_job(api_test_db, status="pending")
    _insert_job(api_test_db, status="failed", last_error="timeout")

    resp = await api_client.get(
        "/queue/jobs?status=failed",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "failed" for item in data["items"])


@pytest.mark.asyncio
async def test_jobs_filter_by_job_type(api_client, api_test_db):
    """GET /queue/jobs?job_type=crawl should filter by job type."""
    _insert_job(api_test_db, job_type="crawl")
    _insert_job(api_test_db, job_type="extract")

    resp = await api_client.get(
        "/queue/jobs?job_type=crawl",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["job_type"] == "crawl" for item in data["items"])


@pytest.mark.asyncio
async def test_jobs_filter_by_lane(api_client, api_test_db):
    """GET /queue/jobs?lane=default should filter by lane."""
    _insert_job(api_test_db, lane="default")
    _insert_job(api_test_db, lane="priority")

    resp = await api_client.get(
        "/queue/jobs?lane=default",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["lane"] == "default" for item in data["items"])


@pytest.mark.asyncio
async def test_jobs_filter_by_source(api_client, api_test_db):
    """GET /queue/jobs?source_id=X should filter by source."""
    source_id = str(uuid.uuid4())
    _insert_job(api_test_db, source_id=source_id)

    resp = await api_client.get(
        f"/queue/jobs?source_id={source_id}",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["source_id"] == source_id for item in data["items"])


@pytest.mark.asyncio
async def test_jobs_includes_attempts_and_lock(api_client, api_test_db):
    """Job items should include attempts, locked_by and last_error."""
    _insert_job(
        api_test_db,
        attempts=2,
        locked_by="worker-1",
        last_error="connection refused",
    )

    resp = await api_client.get(
        "/queue/jobs",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "attempts" in item
    assert "locked_by" in item
    assert "last_error" in item


@pytest.mark.asyncio
async def test_jobs_pagination(api_client, api_test_db):
    """GET /queue/jobs should support limit/offset pagination."""
    for _ in range(5):
        _insert_job(api_test_db)

    resp = await api_client.get(
        "/queue/jobs?limit=2&offset=0",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5
