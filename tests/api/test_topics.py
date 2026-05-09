"""Tests for topic API endpoints — creation and source attachment."""

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
    """Create an isolated test database for API tests."""
    db_name = f"harvester_topic_test_{uuid.uuid4().hex[:8]}"
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


async def _create_source(api_client, name=None):
    """Helper to create a source and return its id."""
    name = name or f"src-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_topic(api_client):
    """POST /topics should create an active topic watch."""
    # Act
    resp = await api_client.post(
        "/topics",
        json={"name": f"topic-{uuid.uuid4().hex[:6]}", "query": "test query"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert "id" in data
    assert data["query"] == "test query"


@pytest.mark.asyncio
async def test_create_topic_with_ttl(api_client):
    """POST /topics with ttl_seconds should set expires_at."""
    # Act
    resp = await api_client.post(
        "/topics",
        json={"name": f"ttl-{uuid.uuid4().hex[:6]}", "ttl_seconds": 3600},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["ttl_seconds"] == 3600


@pytest.mark.asyncio
async def test_attach_source_to_topic(api_client):
    """POST /topics/{id}/sources should attach a source to a topic."""
    # Arrange
    source_id = await _create_source(api_client)
    topic_resp = await api_client.post(
        "/topics",
        json={"name": f"attach-{uuid.uuid4().hex[:6]}"},
        headers={"Authorization": "Bearer test-secret"},
    )
    topic_id = topic_resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/topics/{topic_id}/sources",
        json={"source_id": source_id},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    assert resp.json()["status"] == "attached"


@pytest.mark.asyncio
async def test_attach_duplicate_source_returns_409(api_client):
    """Attaching the same source twice should return 409."""
    # Arrange
    source_id = await _create_source(api_client)
    topic_resp = await api_client.post(
        "/topics",
        json={"name": f"dup-attach-{uuid.uuid4().hex[:6]}"},
        headers={"Authorization": "Bearer test-secret"},
    )
    topic_id = topic_resp.json()["id"]
    await api_client.post(
        f"/topics/{topic_id}/sources",
        json={"source_id": source_id},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — attach the same source again
    resp = await api_client.post(
        f"/topics/{topic_id}/sources",
        json={"source_id": source_id},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_attach_nonexistent_source_returns_404(api_client):
    """Attaching a nonexistent source should return 404."""
    # Arrange
    topic_resp = await api_client.post(
        "/topics",
        json={"name": f"miss-{uuid.uuid4().hex[:6]}"},
        headers={"Authorization": "Bearer test-secret"},
    )
    topic_id = topic_resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/topics/{topic_id}/sources",
        json={"source_id": str(uuid.uuid4())},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_attach_to_nonexistent_topic_returns_404(api_client):
    """Attaching a source to a nonexistent topic should return 404."""
    # Arrange
    source_id = await _create_source(api_client)

    # Act
    resp = await api_client.post(
        f"/topics/{uuid.uuid4()}/sources",
        json={"source_id": source_id},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 404
