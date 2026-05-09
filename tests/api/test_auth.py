"""Tests for API token authentication on mutating endpoints."""

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from harvester.api.app import create_app


@pytest.fixture
def app():
    with patch.dict(os.environ, {
        "HARVESTER_API_TOKEN": "test-secret",
        "HARVESTER_DATABASE_URL": "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres",
    }):
        yield create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_missing_token_returns_401(client):
    """POST /sources/propose without token should return 401."""
    response = await client.post("/sources/propose", json={"name": "test", "kind": "web"})
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
