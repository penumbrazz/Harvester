"""Tests for source API endpoints."""

import os
import uuid
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for API tests.

    Creates a fresh PostgreSQL database, runs Alembic migrations, and yields
    the connection URL. Drops the database on teardown.
    """
    db_name = f"harvester_api_test_{uuid.uuid4().hex[:8]}"
    admin_url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    test_url = admin_url.rsplit("/", 1)[0] + "/" + db_name

    # Create the database
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
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

    # Cleanup — drop the database
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
async def test_propose_source_creates_candidate(api_client):
    """POST /sources/propose should create a candidate source."""
    # Arrange & Act
    resp = await api_client.post(
        "/sources/propose",
        json={
            "name": f"test-src-{uuid.uuid4().hex[:6]}",
            "kind": "web",
            "url": "https://example.com",
        },
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "candidate"
    assert "id" in data


@pytest.mark.asyncio
async def test_propose_duplicate_source_returns_409(api_client):
    """POST /sources/propose with duplicate name should return 409."""
    # Arrange
    name = f"dup-{uuid.uuid4().hex[:6]}"
    await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — propose the same name again
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_promote_source(api_client):
    """POST /sources/{id}/promote should transition candidate -> testing."""
    # Arrange
    resp = await api_client.post(
        "/sources/propose",
        json={"name": f"promo-{uuid.uuid4().hex[:6]}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "testing"


@pytest.mark.asyncio
async def test_pause_watched_source(api_client):
    """POST /sources/{id}/pause should transition watched -> paused."""
    # Arrange — create and promote to watched
    name = f"pause-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    # Promote twice: candidate -> testing -> watched
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_promote_nonexistent_source_returns_404(api_client):
    """POST /sources/{id}/promote with invalid id should return 404."""
    # Act
    resp = await api_client.post(
        f"/sources/{uuid.uuid4()}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_transition_persists_rejection_audit(api_client, api_test_db):
    """Illegal transition must persist a rejection audit event."""
    # Arrange — create a candidate source
    resp = await api_client.post(
        "/sources/propose",
        json={"name": f"audit-{uuid.uuid4().hex[:6]}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act — try to pause a candidate (illegal: candidate -> paused is not allowed)
    resp = await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 400

    # Assert — rejection audit must be in the database
    engine = create_engine(api_test_db)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT action FROM audit_events "
                "WHERE entity_id = :eid AND action = 'status_change_rejected'"
            ),
            {"eid": source_id},
        ).fetchone()
    engine.dispose()
    assert row is not None, "Rejection audit event must be persisted after illegal transition"
    assert row[0] == "status_change_rejected"
