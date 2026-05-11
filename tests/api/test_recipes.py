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


# ---------------------------------------------------------------------------
# GET /recipes — list endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_recipes_requires_auth(api_client):
    """GET /recipes without token returns 401."""
    resp = await api_client.get("/recipes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_recipes_returns_empty(api_client):
    """GET /recipes returns a paginated response."""
    resp = await api_client.get(
        "/recipes",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.asyncio
async def test_list_recipes_returns_created_recipes(api_client):
    """GET /recipes returns recipes that were previously created."""
    headers = {"Authorization": "Bearer test-secret"}

    # Create two recipes
    await api_client.post(
        "/recipes",
        json={"name": f"list-a-{uuid.uuid4().hex[:6]}", "executor": "http_fetch"},
        headers=headers,
    )
    await api_client.post(
        "/recipes",
        json={"name": f"list-b-{uuid.uuid4().hex[:6]}", "executor": "rss_parse"},
        headers=headers,
    )

    resp = await api_client.get("/recipes", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 2

    # Verify required fields present
    for item in data["items"]:
        assert "id" in item
        assert "name" in item
        assert "executor" in item
        assert "approval_status" in item
        assert "risk_level" in item
        assert "version" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_list_recipes_filter_by_approval_status(api_client):
    """GET /recipes?approval_status=approved returns only approved recipes."""
    headers = {"Authorization": "Bearer test-secret"}

    # Create and approve one recipe
    resp = await api_client.post(
        "/recipes",
        json={"name": f"approved-{uuid.uuid4().hex[:6]}", "executor": "firecrawl"},
        headers=headers,
    )
    recipe_id = resp.json()["id"]
    await api_client.post(f"/recipes/{recipe_id}/approve", headers=headers)

    # Create another pending recipe
    await api_client.post(
        "/recipes",
        json={"name": f"pending-{uuid.uuid4().hex[:6]}", "executor": "http_fetch"},
        headers=headers,
    )

    # Filter for approved only
    resp = await api_client.get(
        "/recipes?approval_status=approved",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert all(r["approval_status"] == "approved" for r in data["items"])


@pytest.mark.asyncio
async def test_list_recipes_filter_by_executor(api_client):
    """GET /recipes?executor=http_fetch returns only matching recipes."""
    headers = {"Authorization": "Bearer test-secret"}

    await api_client.post(
        "/recipes",
        json={"name": f"exec-a-{uuid.uuid4().hex[:6]}", "executor": "http_fetch"},
        headers=headers,
    )
    await api_client.post(
        "/recipes",
        json={"name": f"exec-b-{uuid.uuid4().hex[:6]}", "executor": "rss_parse"},
        headers=headers,
    )

    resp = await api_client.get(
        "/recipes?executor=http_fetch",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert all(r["executor"] == "http_fetch" for r in data["items"])
