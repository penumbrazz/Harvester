"""Shared pytest fixtures for Harvester tests."""

import pytest
from httpx import ASGITransport, AsyncClient

# Re-export database fixtures from tests/db/conftest.py so they are
# discoverable by all test modules under tests/.
pytest_plugins = ["tests.db.conftest"]


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
