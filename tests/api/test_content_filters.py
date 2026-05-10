"""Tests for content item list filtering (source, topic, type, status)."""

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
    insert_topic,
)


@pytest.fixture(scope="module")
def filter_test_db():
    """Create an isolated test database for filter tests."""
    db_name = f"harvester_filter_test_{uuid.uuid4().hex[:8]}"
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
async def filter_api_client(filter_test_db):
    """Create an async API test client with database configured."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": filter_test_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# --- Source filter ---


@pytest.mark.asyncio
async def test_filter_by_source_id(filter_api_client, filter_test_db):
    """GET /items/content?source_id=X should only return items from that source."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_a = insert_source(session, "filter-src-a")
        src_b = insert_source(session, "filter-src-b")
        insert_content_item(session, src_a, "Source A Article")
        insert_content_item(session, src_b, "Source B Article")
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?source_id={src_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["source_id"] == str(src_a)
    assert data["items"][0]["title"] == "Source A Article"


# --- Topic filter ---


@pytest.mark.asyncio
async def test_filter_by_topic_watch_id(filter_api_client, filter_test_db):
    """GET /items/content?topic_watch_id=X should only return items from that topic."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "topic-filter-src")
        tw_a = insert_topic(session, "filter-topic-a")
        tw_b = insert_topic(session, "filter-topic-b")
        insert_content_item(session, src_id, "Topic A Article", topic_watch_id=tw_a)
        insert_content_item(session, src_id, "Topic B Article", topic_watch_id=tw_b)
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?topic_watch_id={tw_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Topic A Article"


# --- Status filter ---


@pytest.mark.asyncio
async def test_filter_by_status(filter_api_client, filter_test_db):
    """GET /items/content?status=active should only return active items."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "status-filter-src")
        ci_a = insert_content_item(session, src_id, "Active Article")
        ci_d = insert_content_item(session, src_id, "Deduped Article")
        # Set one item to deduped status
        session.execute(
            text("UPDATE content_items SET status = 'deduped' WHERE id = :id"),
            {"id": ci_d},
        )
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?status=active&source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Active Article"


# --- Item type filter ---


@pytest.mark.asyncio
async def test_filter_by_item_type(filter_api_client, filter_test_db):
    """GET /items/content?item_type=article should only return articles."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "type-filter-src")
        ci_a = insert_content_item(session, src_id, "Type Article")
        # Insert a different item_type manually
        ci_b = insert_content_item(session, src_id, "Type Page")
        session.execute(
            text("UPDATE content_items SET item_type = 'page' WHERE id = :id"),
            {"id": ci_b},
        )
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?item_type=article&source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["item_type"] == "article"


# --- Combined filters ---


@pytest.mark.asyncio
async def test_combined_source_and_status_filter(filter_api_client, filter_test_db):
    """GET /items/content?source_id=X&status=active should combine filters."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_a = insert_source(session, "combined-src-a")
        src_b = insert_source(session, "combined-src-b")
        insert_content_item(session, src_a, "A Active Article")
        ci_b = insert_content_item(session, src_b, "B Active Article")
        ci_a2 = insert_content_item(session, src_a, "A Deduped Article")
        session.execute(
            text("UPDATE content_items SET status = 'deduped' WHERE id = :id"),
            {"id": ci_a2},
        )
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?source_id={src_a}&status=active",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "A Active Article"


# --- Source name join ---


@pytest.mark.asyncio
async def test_content_list_includes_source_name(filter_api_client, filter_test_db):
    """Content list should include source_name for display."""
    engine = create_engine(filter_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "source-name-display")
        insert_content_item(session, src_id, "Named Source Article")
        session.commit()
    engine.dispose()

    response = await filter_api_client.get(
        f"/items/content?source_id={src_id}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["source_name"] == "source-name-display"
