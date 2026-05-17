"""Tests for crawl run list API endpoint.

Covers: pagination, status filter, source filter, error fields.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for crawl run list API tests."""
    db_name = f"harvester_crawl_list_{uuid.uuid4().hex[:8]}"
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


def _insert_source(db_url: str, *, name_prefix="crawl-list"):
    source_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(bind=create_engine(db_url)) as session:
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
                name=f"{name_prefix}-{source_id.hex[:8]}",
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
        session.commit()
    return source_id


def _insert_crawl_run(
    db_url: str,
    source_id: uuid.UUID,
    *,
    status="completed",
    error_message=None,
    http_status=None,
):
    run_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(bind=create_engine(db_url)) as session:
        session.execute(
            sa.text(
                "INSERT INTO crawl_runs "
                "(id, source_id, status, http_status, error_message, "
                "started_at, completed_at, created_at) VALUES "
                "(:id, :source_id, :status, :http_status, :error_message, "
                ":started, :completed, :created)"
            ),
            dict(
                id=run_id,
                source_id=source_id,
                status=status,
                http_status=http_status,
                error_message=error_message,
                started=now,
                completed=now if status == "completed" else None,
                created=now,
            ),
        )
        session.commit()
    return run_id


@pytest.mark.asyncio
async def test_crawl_runs_requires_auth(api_client):
    """GET /crawl/runs should require API token."""
    resp = await api_client.get("/crawl/runs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_crawl_runs_returns_empty(api_client):
    """GET /crawl/runs should return empty list when no runs exist."""
    resp = await api_client.get(
        "/crawl/runs",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_crawl_runs_returns_items(api_client, api_test_db):
    """GET /crawl/runs should return crawl run records."""
    source_id = _insert_source(api_test_db)
    _insert_crawl_run(api_test_db, source_id)

    resp = await api_client.get(
        "/crawl/runs",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "id" in item
    assert "status" in item
    assert "source_id" in item
    assert "created_at" in item


@pytest.mark.asyncio
async def test_crawl_runs_status_filter(api_client, api_test_db):
    """GET /crawl/runs?status=failed should filter by status."""
    source_id = _insert_source(api_test_db)
    _insert_crawl_run(api_test_db, source_id, status="completed")
    _insert_crawl_run(api_test_db, source_id, status="failed", error_message="timeout")

    resp = await api_client.get(
        "/crawl/runs?status=failed",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "failed" for item in data["items"])


@pytest.mark.asyncio
async def test_crawl_runs_source_filter(api_client, api_test_db):
    """GET /crawl/runs?source_id=X should filter by source."""
    source_id = _insert_source(api_test_db)
    _insert_crawl_run(api_test_db, source_id)

    resp = await api_client.get(
        f"/crawl/runs?source_id={source_id}",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["source_id"] == str(source_id) for item in data["items"])


@pytest.mark.asyncio
async def test_crawl_runs_pagination(api_client, api_test_db):
    """GET /crawl/runs should support limit/offset pagination."""
    source_id = _insert_source(api_test_db)
    for _ in range(5):
        _insert_crawl_run(api_test_db, source_id)

    resp = await api_client.get(
        "/crawl/runs?limit=2&offset=0",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5
    assert data["limit"] == 2
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_crawl_run_item_fields(api_client, api_test_db):
    """Crawl run items should include expected fields."""
    source_id = _insert_source(api_test_db)
    _insert_crawl_run(
        api_test_db,
        source_id,
        status="failed",
        error_message="connection refused",
        http_status=500,
    )

    resp = await api_client.get(
        "/crawl/runs",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    failed = [i for i in data["items"] if i["status"] == "failed"]
    assert len(failed) >= 1
    item = failed[0]
    assert item["error_message"] == "connection refused"
    assert item["http_status"] == 500
