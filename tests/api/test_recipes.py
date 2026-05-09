"""Tests for recipe API endpoints — creation and approval."""

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
    db_name = f"harvester_recipe_test_{uuid.uuid4().hex[:8]}"
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
async def test_create_recipe(api_client):
    """POST /recipes should create a pending recipe."""
    # Act
    resp = await api_client.post(
        "/recipes",
        json={
            "name": f"recipe-{uuid.uuid4().hex[:6]}",
            "executor": "http_fetch",
            "config": {"url": "https://example.com/feed"},
        },
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["approval_status"] == "pending"
    assert data["executor"] == "http_fetch"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_recipe_with_unknown_executor_returns_400(api_client):
    """POST /recipes with unsupported executor should return 400."""
    # Act
    resp = await api_client.post(
        "/recipes",
        json={"name": f"bad-{uuid.uuid4().hex[:6]}", "executor": "unknown_executor"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_recipe(api_client):
    """POST /recipes/{id}/approve should transition pending -> approved."""
    # Arrange
    resp = await api_client.post(
        "/recipes",
        json={
            "name": f"approve-{uuid.uuid4().hex[:6]}",
            "executor": "firecrawl",
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    recipe_id = resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/recipes/{recipe_id}/approve",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["approval_status"] == "approved"


@pytest.mark.asyncio
async def test_approve_nonexistent_recipe_returns_404(api_client):
    """POST /recipes/{id}/approve with invalid id should return 404."""
    # Act
    resp = await api_client.post(
        f"/recipes/{uuid.uuid4()}/approve",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_already_approved_returns_400(api_client):
    """Approving an already-approved recipe should return 400."""
    # Arrange
    resp = await api_client.post(
        "/recipes",
        json={
            "name": f"dbl-{uuid.uuid4().hex[:6]}",
            "executor": "rss_parse",
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    recipe_id = resp.json()["id"]
    await api_client.post(
        f"/recipes/{recipe_id}/approve",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — approve again
    resp = await api_client.post(
        f"/recipes/{recipe_id}/approve",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400
