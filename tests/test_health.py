"""Test health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint():
    """Assert GET /health returns 200 and {"status": "ok"}."""
    from harvester.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
