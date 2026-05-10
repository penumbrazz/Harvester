"""Regression tests confirming search API responses are frontend-friendly and safe.

Verifies that keyword/vector search responses do NOT expose raw HTML, API payloads,
or internal storage URIs. These tests complement test_search.py by focusing on
frontend display concerns.
"""

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
    insert_chunk,
    insert_content_item,
    insert_item_version,
    insert_source,
)


@pytest.fixture(scope="module")
def search_compat_db():
    """Create an isolated test database for search compatibility tests."""
    db_name = f"harvester_search_compat_{uuid.uuid4().hex[:8]}"
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
async def search_compat_client(search_compat_db):
    """Create an async API test client with database configured."""
    with patch.dict(
        os.environ,
        {
            "HARVESTER_API_TOKEN": "test-secret",
            "HARVESTER_DATABASE_URL": search_compat_db,
        },
    ):
        from harvester.api.app import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


FORBIDDEN_RAW_FIELDS = {"storage_uri", "content_hash", "payload", "raw_html", "byte_size"}


@pytest.mark.asyncio
async def test_keyword_search_no_raw_fields(search_compat_client, search_compat_db):
    """Keyword search response must not expose raw evidence fields."""
    engine = create_engine(search_compat_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "no-raw-kw-src")
        ci_id = insert_content_item(
            session,
            src_id,
            "No Raw Keyword Article",
            canonical_url="https://example.com/no-raw",
        )
        insert_item_version(session, ci_id)
        session.commit()
    engine.dispose()

    response = await search_compat_client.get(
        "/items/search?q=No Raw Keyword",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    for item in data["items"]:
        for field in FORBIDDEN_RAW_FIELDS:
            assert field not in item, f"Keyword search item must not contain {field}"


@pytest.mark.asyncio
async def test_vector_search_no_raw_fields(search_compat_client, search_compat_db):
    """Vector search response must not expose raw evidence fields."""
    engine = create_engine(search_compat_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "no-raw-vec-src")
        ci_id = insert_content_item(session, src_id, "No Raw Vector Article")
        iv_id = insert_item_version(session, ci_id)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("NoRaw")
        insert_chunk(
            session,
            iv_id,
            0,
            "no raw vector chunk text",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()

    response = await search_compat_client.get(
        "/items/search?q=NoRaw&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    for item in data["items"]:
        for field in FORBIDDEN_RAW_FIELDS:
            assert field not in item, f"Vector search item must not contain {field}"


@pytest.mark.asyncio
async def test_keyword_search_has_traceable_fields(search_compat_client, search_compat_db):
    """Keyword search response must have traceable fields for frontend display."""
    engine = create_engine(search_compat_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "trace-kw-src")
        ci_id = insert_content_item(
            session,
            src_id,
            "Traceable Keyword Article",
            canonical_url="https://example.com/traceable",
        )
        insert_item_version(session, ci_id)
        session.commit()
    engine.dispose()

    response = await search_compat_client.get(
        "/items/search?q=Traceable",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    # Must have traceable fields
    assert "item_id" in item
    assert "version_id" in item
    assert "source_id" in item
    assert "title" in item
    assert "canonical_url" in item
    assert "created_at" in item
    assert "mode" in item
    assert item["mode"] == "keyword"


@pytest.mark.asyncio
async def test_vector_search_has_traceable_fields(search_compat_client, search_compat_db):
    """Vector search response must have traceable fields for frontend display."""
    engine = create_engine(search_compat_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "trace-vec-src")
        ci_id = insert_content_item(session, src_id, "Traceable Vector Article")
        iv_id = insert_item_version(session, ci_id)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("TraceableVec")
        insert_chunk(
            session,
            iv_id,
            0,
            "traceable vector chunk text",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()

    response = await search_compat_client.get(
        "/items/search?q=TraceableVec&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    # Must have traceable fields
    assert "chunk_id" in item
    assert "item_version_id" in item
    assert "content_item_id" in item
    assert "title" in item
    assert "text" in item
    assert "distance" in item
    assert "mode" in item
    assert item["mode"] == "vector"
    assert isinstance(item["distance"], float)


@pytest.mark.asyncio
async def test_vector_search_503_when_embedding_unavailable(search_compat_client):
    """Vector search must return 503 when embedding adapter is unavailable."""
    with patch(
        "harvester.adapters.embedding_settings.create_embedding_adapter",
        side_effect=RuntimeError("No embedding service configured"),
    ):
        response = await search_compat_client.get(
            "/items/search?q=test&mode=vector",
            headers={"Authorization": "Bearer test-secret"},
        )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "unavailable" in detail.lower() or "embedding" in detail.lower()
