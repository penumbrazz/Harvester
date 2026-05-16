"""Tests for GET /items/content API endpoint (content item list)."""

import os
import uuid
from unittest.mock import patch

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from tests.utils.factories import (
    insert_content_item,
    insert_item_version,
    insert_source,
)


@pytest.fixture(scope="module")
def content_test_db():
    """Create an isolated test database for content item API tests."""
    db_name = f"harvester_content_test_{uuid.uuid4().hex[:8]}"
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
async def content_api_client(content_test_db):
    """Create an async API test client with database configured."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": content_test_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# --- Auth tests ---


@pytest.mark.asyncio
async def test_content_list_requires_api_token(content_api_client):
    """GET /items/content without token should return 401."""
    response = await content_api_client.get("/items/content")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_content_list_wrong_token_returns_401(content_api_client):
    """GET /items/content with wrong token should return 401."""
    response = await content_api_client.get(
        "/items/content",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


# --- Empty list ---


@pytest.mark.asyncio
async def test_content_list_returns_empty_when_no_items(content_api_client):
    """GET /items/content should return 200 with empty items when db is empty."""
    response = await content_api_client.get(
        "/items/content",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 0


# --- Field validation ---


@pytest.mark.asyncio
async def test_content_list_returns_expected_fields(
    content_api_client, content_test_db
):
    """Each content item must contain id, item_type, source_id, title, canonical_url, status, created_at, updated_at."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "content-fields-src")
        insert_content_item(
            session,
            src_id,
            "Field Validation Article",
            canonical_url="https://example.com/fields",
        )
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        "/items/content",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    expected_fields = {
        "id",
        "item_type",
        "source_id",
        "title",
        "canonical_url",
        "status",
        "created_at",
        "updated_at",
    }
    assert expected_fields.issubset(set(item.keys()))
    assert item["title"] == "Field Validation Article"
    assert item["canonical_url"] == "https://example.com/fields"
    assert item["status"] == "active"
    assert item["item_type"] == "article"


# --- Pagination ---


@pytest.mark.asyncio
async def test_content_list_default_pagination(content_api_client, content_test_db):
    """Default pagination should use limit=20, offset=0."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "pagination-src")
        for i in range(25):
            insert_content_item(session, src_id, f"Pagination Item {i:03d}")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content?source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 20


@pytest.mark.asyncio
async def test_content_list_custom_limit(content_api_client, content_test_db):
    """GET /items/content?limit=5 should return at most 5 items."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "limit-src")
        for i in range(10):
            insert_content_item(session, src_id, f"Limit Item {i:03d}")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content?limit=5&source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_content_list_offset(content_api_client, content_test_db):
    """GET /items/content?offset=5 should skip first 5 items for a given source."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "offset-src")
        for i in range(10):
            insert_content_item(session, src_id, f"Offset Item {i:03d}")
        session.commit()
    engine.dispose()

    # Use source_id filter to isolate test data
    response = await content_api_client.get(
        f"/items/content?offset=5&source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    # 10 items total, offset 5 = 5 remaining
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_content_list_total_count(content_api_client, content_test_db):
    """Response should include total count for pagination UI."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "total-src")
        for i in range(15):
            insert_content_item(session, src_id, f"Total Item {i:03d}")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content?limit=5&source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] == 15
    assert len(data["items"]) == 5


# --- Sorting ---


@pytest.mark.asyncio
async def test_content_list_sorted_by_updated_at_desc(
    content_api_client, content_test_db
):
    """Items should be sorted by updated_at descending (most recent first)."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "sort-src")
        insert_content_item(session, src_id, "Alpha Article")
        insert_content_item(session, src_id, "Beta Article")
        insert_content_item(session, src_id, "Gamma Article")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content?source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    # Most recently inserted should appear first
    assert data["items"][0]["title"] == "Gamma Article"


# --- No raw payload ---


@pytest.mark.asyncio
async def test_content_list_does_not_return_raw_payload(
    content_api_client, content_test_db
):
    """Response must not contain raw HTML or API payload fields."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "no-raw-src")
        insert_content_item(session, src_id, "No Raw Test")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        "/items/content",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    # Must not expose raw-related fields
    assert "storage_uri" not in item
    assert "content_hash" not in item
    assert "payload" not in item
    assert "raw_html" not in item


# --- Content detail endpoint ---


@pytest.mark.asyncio
async def test_content_detail_returns_item_with_version(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return item metadata + latest version text."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "detail-src")
        ci_id = insert_content_item(
            session,
            src_id,
            "Detail Test Article",
            canonical_url="https://example.com/detail",
        )
        insert_item_version(
            session,
            ci_id,
            normalized_text="Full article body text here.",
            language="en",
        )
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ci_id)
    assert data["title"] == "Detail Test Article"
    assert data["source_name"] == "detail-src"
    assert data["latest_version"] is not None
    assert data["latest_version"]["normalized_text"] == "Full article body text here."
    assert data["latest_version"]["language"] == "en"


@pytest.mark.asyncio
async def test_content_detail_returns_null_version_when_no_version(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return latest_version as null when no versions exist."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "no-version-src")
        ci_id = insert_content_item(session, src_id, "No Version Article")
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latest_version"] is None


@pytest.mark.asyncio
async def test_content_detail_returns_404_for_missing_id(content_api_client):
    """GET /items/content/{id} should return 404 for non-existent id."""
    fake_id = uuid.uuid4()
    response = await content_api_client.get(
        f"/items/content/{fake_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_content_detail_returns_latest_of_multiple_versions(
    content_api_client, content_test_db
):
    """GET /items/content/{id} should return the most recent version."""
    engine = create_engine(content_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "multi-version-src")
        ci_id = insert_content_item(session, src_id, "Multi Version Article")
        insert_item_version(
            session, ci_id, normalized_text="First version text", language="en"
        )
        insert_item_version(
            session, ci_id, normalized_text="Second version text", language="en"
        )
        session.commit()
    engine.dispose()

    response = await content_api_client.get(
        f"/items/content/{ci_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latest_version"]["normalized_text"] == "Second version text"
