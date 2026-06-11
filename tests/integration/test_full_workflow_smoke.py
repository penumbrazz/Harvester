"""Integration test: full lifecycle smoke test via HTTP API.

Exercises the complete Harvester workflow end-to-end:
1. Propose source (candidate)
2. Promote source (candidate -> testing -> watched)
3. Create recipe (pending)
4. Approve recipe (pending -> approved)
5. Trigger crawl run (mocked adapter)
6. Verify audit trail persisted

This test uses an isolated test database per module and mocks the
network-facing crawl adapter so it runs without external dependencies.
Enable live crawl by setting HARVESTER_ENABLE_LIVE_CRAWL=1.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from alembic import command
from harvester.adapters.types import CrawlResult
from harvester.domain.fetch_policy import FetchPolicyResult
from harvester.jobs.archive import ArchiveWriteResult

LIVE_CRAWL_ENABLED = os.environ.get("HARVESTER_ENABLE_LIVE_CRAWL", "").strip() == "1"

ADMIN_URL = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"


@pytest.fixture(scope="module")
def workflow_db_url():
    """Create an isolated test database for the full workflow smoke test.

    Creates a fresh PostgreSQL database, runs Alembic migrations to head,
    and yields the connection URL. Drops the database on teardown.
    """
    db_name = f"harvester_workflow_test_{uuid.uuid4().hex[:8]}"
    test_url = ADMIN_URL.rsplit("/", 1)[0] + "/" + db_name

    # Create the database
    admin_engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    # Run Alembic migrations
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    if env_backup:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    yield test_url

    # Cleanup -- terminate connections and drop the database
    admin_engine2 = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine2.connect() as conn:
        conn.execute(
            text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}'"
            )
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    admin_engine2.dispose()


@pytest.fixture
async def api_client(workflow_db_url):
    """Create an async API test client with the workflow test database."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": workflow_db_url,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _make_archive_result():
    """Return a mocked ArchiveWriteResult for successful crawl."""
    return ArchiveWriteResult(
        relative_path="2026/05/workflow_smoke.raw",
        storage_uri="file:///archive/2026/05/workflow_smoke.raw",
        content_hash="sha256:workflow_test_hash",
        byte_size=256,
        content_type="text/html",
        retention_days=7,
        retain_until=datetime.now(UTC) + timedelta(days=7),
    )


@pytest.mark.skipif(
    not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set"
)
@pytest.mark.asyncio
async def test_full_workflow_via_api(api_client, workflow_db_url):
    """Full lifecycle: propose source -> promote -> create recipe -> approve
    -> trigger crawl -> verify audit trail.

    This test is gated behind HARVESTER_ENABLE_LIVE_CRAWL=1 because it
    exercises the real crawl adapter (no mocking). Only run when you have
    Firecrawl or equivalent infrastructure available.
    """
    headers = {"Authorization": "Bearer test-secret"}
    suffix = uuid.uuid4().hex[:6]

    # 1. Propose source -> candidate
    resp = await api_client.post(
        "/sources/propose",
        json={
            "name": f"workflow-src-{suffix}",
            "kind": "web",
            "url": "https://finance.sina.com.cn/7x24/",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]
    assert resp.json()["status"] == "candidate"

    # 2. Promote candidate -> testing -> watched
    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "testing"

    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "watched"

    # 3. Create recipe -> pending
    resp = await api_client.post(
        "/recipes",
        json={
            "name": f"workflow-recipe-{suffix}",
            "executor": "http_fetch",
            "config": {"url": "https://finance.sina.com.cn/7x24/"},
            "risk_level": "low",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    recipe_id = resp.json()["id"]
    assert resp.json()["approval_status"] == "pending"

    # 4. Approve recipe -> approved
    resp = await api_client.post(
        f"/recipes/{recipe_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "approved"

    # 5. Trigger crawl (may succeed or fail depending on Firecrawl availability)
    resp = await api_client.post(
        "/crawl/run",
        json={
            "source_id": source_id,
            "recipe_id": recipe_id,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "crawl_run_id" in data or "id" in data

    # 6. Verify audit trail -- status_change events must exist
    engine = create_engine(workflow_db_url)
    with engine.connect() as conn:
        audits = conn.execute(
            sa.text(
                "SELECT action, after_state FROM audit_events "
                "WHERE entity_id = :eid "
                "ORDER BY created_at"
            ),
            {"eid": source_id},
        ).fetchall()
        actions = [r[0] for r in audits]
        assert "status_change" in actions
    engine.dispose()


@pytest.mark.asyncio
async def test_full_workflow_mocked_crawl(api_client, workflow_db_url):
    """Full lifecycle with mocked crawl adapter -- runs without external deps.

    This is the default CI-safe variant of the full workflow smoke test.
    All network calls are mocked so it works in any environment.
    """
    headers = {"Authorization": "Bearer test-secret"}
    suffix = uuid.uuid4().hex[:6]

    # 1. Propose source -> candidate
    resp = await api_client.post(
        "/sources/propose",
        json={
            "name": f"mock-src-{suffix}",
            "kind": "web",
            "url": "https://example.com/smoke-test",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]
    assert resp.json()["status"] == "candidate"

    # 2. Promote candidate -> testing -> watched
    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "testing"

    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "watched"

    # 3. Create recipe -> pending
    resp = await api_client.post(
        "/recipes",
        json={
            "name": f"mock-recipe-{suffix}",
            "executor": "http_fetch",
            "config": {"url": "https://example.com/smoke-test"},
            "risk_level": "low",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    recipe_id = resp.json()["id"]
    assert resp.json()["approval_status"] == "pending"

    # 4. Approve recipe -> approved
    resp = await api_client.post(
        f"/recipes/{recipe_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "approved"

    # 5. Trigger crawl with mocked adapter
    crawl_result = CrawlResult(
        original_url="https://example.com/smoke-test",
        final_url="https://example.com/smoke-test",
        status_code=200,
        content_type="text/html",
        payload_text="<html><body>smoke test content</body></html>",
        error=None,
    )

    with (
        patch(
            "harvester.jobs.crawl_execution.check_fetch_policy",
            return_value=FetchPolicyResult(allowed=True),
        ),
        patch(
            "harvester.jobs.crawl_execution.execute_adapter_crawl",
            return_value=crawl_result,
        ),
        patch(
            "harvester.jobs.crawl_execution.write_archive",
            return_value=_make_archive_result(),
        ),
    ):
        resp = await api_client.post(
            "/crawl/run",
            json={
                "source_id": str(source_id),
                "recipe_id": str(recipe_id),
            },
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "crawl_run_id" in data
    assert data["status"] == "completed"
    assert "raw_object_id" in data

    crawl_run_id = data["crawl_run_id"]

    # 6. Verify audit trail -- status_change events for source
    engine = create_engine(workflow_db_url)
    with engine.connect() as conn:
        # Source status transitions produce audit events
        source_audits = conn.execute(
            sa.text(
                "SELECT action, after_state FROM audit_events "
                "WHERE entity_id = :eid "
                "ORDER BY created_at"
            ),
            {"eid": str(source_id)},
        ).fetchall()
        source_actions = [r[0] for r in source_audits]
        assert "status_change" in source_actions

        # Verify at least two status_change events (candidate->testing, testing->watched)
        status_changes = [r for r in source_audits if r[0] == "status_change"]
        assert len(status_changes) >= 2

        # Crawl run should be recorded
        crawl_audits = conn.execute(
            sa.text(
                "SELECT action FROM audit_events "
                "WHERE entity_id = :eid "
                "ORDER BY created_at"
            ),
            {"eid": str(crawl_run_id)},
        ).fetchall()
        # Crawl run may or may not have its own audit events;
        # the important thing is the source status changes are captured
        assert len(source_audits) >= 2

    engine.dispose()
