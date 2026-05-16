"""Tests for API token authentication on mutating endpoints."""

import os
import uuid
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine

from harvester.api.app import create_app


def _get_admin_url() -> str:
    url = os.environ.get("HARVESTER_DATABASE_URL", "")
    if not url:
        url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    parts = url.rsplit("/", 1)
    return parts[0] + "/postgres"


@pytest.fixture(scope="module")
def auth_test_db():
    """Create an isolated database for auth tests, dropped after the module."""
    db_name = f"harvester_auth_test_{uuid.uuid4().hex[:8]}"
    admin_url = _get_admin_url()
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    db_url = admin_url.rsplit("/", 1)[0] + f"/{db_name}"
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
    if env_backup is not None:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    yield db_url

    teardown_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with teardown_engine.connect() as conn:
        conn.execute(
            sa.text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}'"
            )
        )
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    teardown_engine.dispose()


@pytest.fixture()
def app(auth_test_db):
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": auth_test_db,
        },
    ):
        yield create_app()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_missing_token_returns_401(client):
    """POST /sources/propose without token should return 401."""
    response = await client.post(
        "/sources/propose", json={"name": "test", "kind": "web"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_token_returns_401(client):
    """POST /sources/propose with wrong token should return 401."""
    response = await client.post(
        "/sources/propose",
        json={"name": "test", "kind": "web"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_token_accepted(client):
    """POST /sources/propose with valid token should not return 401."""
    response = await client.post(
        "/sources/propose",
        json={"name": "test", "kind": "web", "url": "https://example.com"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_get_health_no_auth_required():
    """GET /health should not require authentication."""
    with patch.dict(os.environ, {"HARVESTER_API_TOKEN": "test-secret"}):
        app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_no_token_configured_returns_401(auth_test_db):
    """Mutating endpoints must return 401 when HARVESTER_API_TOKEN is not set."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "",
            "HARVESTER_DATABASE_URL": auth_test_db,
        },
        clear=False,
    ):
        os.environ.pop("HARVESTER_API_TOKEN", None)
        app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/sources/propose",
            json={"name": "test-no-token", "kind": "web"},
        )
        assert response.status_code == 401
        assert "not configured" in response.json()["detail"].lower()
