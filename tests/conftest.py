"""Shared pytest fixtures for Harvester tests."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """Create a test FastAPI application instance.

    Returns:
        FastAPI application configured for testing.
    """
    from harvester.api.app import create_app
    return create_app()


@pytest.fixture
async def async_client(app):
    """Create an async HTTP client for testing the FastAPI app.

    Args:
        app: FastAPI application fixture.

    Yields:
        AsyncClient configured for the test app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
