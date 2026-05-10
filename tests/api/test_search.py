"""Tests for GET /items/search API endpoint."""

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
    insert_topic,
)


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for API tests."""
    db_name = f"harvester_search_test_{uuid.uuid4().hex[:8]}"
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


# --- Auth tests ---


@pytest.mark.asyncio
async def test_search_requires_api_token(api_client):
    """GET /items/search without token should return 401."""
    response = await api_client.get("/items/search?q=test")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_wrong_token_returns_401(api_client):
    """GET /items/search with wrong token should return 401."""
    response = await api_client.get(
        "/items/search?q=test",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


# --- Parameter validation tests ---


@pytest.mark.asyncio
async def test_search_missing_q_returns_error(api_client):
    """GET /items/search without q parameter should return 422."""
    response = await api_client.get(
        "/items/search",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_blank_q_returns_empty(api_client):
    """GET /items/search?q=   (whitespace-only) should return 200 with empty results."""
    response = await api_client.get(
        "/items/search?q=%20%20%20",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


# --- Success scenarios ---


@pytest.mark.asyncio
async def test_search_returns_matching_items(api_client, api_test_db):
    """GET /items/search?q=Python should return items with matching titles."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "search-src-1")
        ci_id = insert_content_item(session, src_id, "Python Async Programming Guide")
        insert_item_version(session, ci_id)
        ci2_id = insert_content_item(session, src_id, "Rust Ownership Model")
        insert_item_version(session, ci2_id)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Python",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Python Async Programming Guide"


@pytest.mark.asyncio
async def test_search_filter_by_source_id(api_client, api_test_db):
    """GET /items/search?q=Python&source_id=X should only return items from that source."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_a = insert_source(session, "filter-src-a")
        src_b = insert_source(session, "filter-src-b")
        ci_a = insert_content_item(session, src_a, "Python Data Analysis")
        insert_item_version(session, ci_a)
        ci_b = insert_content_item(session, src_b, "Python Web Development")
        insert_item_version(session, ci_b)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        f"/items/search?q=Python&source_id={src_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["source_id"] == str(src_a)


@pytest.mark.asyncio
async def test_search_filter_by_topic_watch_id(api_client, api_test_db):
    """GET /items/search?q=Python&topic_watch_id=X should only return items from that topic."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "topic-src")
        tw_a = insert_topic(session, "topic-a")
        tw_b = insert_topic(session, "topic-b")
        ci_a = insert_content_item(
            session, src_id, "Python ML Guide", topic_watch_id=tw_a
        )
        insert_item_version(session, ci_a)
        ci_b = insert_content_item(
            session, src_id, "Python DL Guide", topic_watch_id=tw_b
        )
        insert_item_version(session, ci_b)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        f"/items/search?q=Python&topic_watch_id={tw_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Python ML Guide"


@pytest.mark.asyncio
async def test_search_limit_parameter(api_client, api_test_db):
    """GET /items/search?q=Python&limit=1 should return at most 1 result."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "limit-src")
        for i in range(3):
            ci = insert_content_item(session, src_id, f"Python Article {i}")
            insert_item_version(session, ci)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Python&limit=1",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_search_offset_parameter(api_client, api_test_db):
    """GET /items/search?q=Python&offset=2 should skip first 2 results."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "offset-src")
        for i in range(4):
            ci = insert_content_item(session, src_id, f"Python Offset {i}")
            insert_item_version(session, ci)
        session.commit()
    engine.dispose()

    response_no_offset = await api_client.get(
        "/items/search?q=Python",
        headers={"Authorization": "Bearer test-secret"},
    )
    total = len(response_no_offset.json()["items"])

    response_offset = await api_client.get(
        "/items/search?q=Python&offset=2",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response_offset.status_code == 200
    assert len(response_offset.json()["items"]) <= max(0, total - 2)


# --- Response field tests ---


@pytest.mark.asyncio
async def test_search_response_contains_expected_fields(api_client, api_test_db):
    """Each search result must contain item_id, version_id, source_id, title, canonical_url, created_at."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "fields-src")
        ci_id = insert_content_item(
            session,
            src_id,
            "Field Test Article",
            canonical_url="https://example.com/field-test",
        )
        insert_item_version(session, ci_id)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Field",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    expected_fields = {
        "item_id",
        "version_id",
        "source_id",
        "title",
        "canonical_url",
        "created_at",
    }
    assert expected_fields.issubset(set(item.keys()))
    assert item["title"] == "Field Test Article"
    assert item["canonical_url"] == "https://example.com/field-test"
    assert item["source_id"] == str(src_id)


# --- Vector search mode tests ---


@pytest.mark.asyncio
async def test_vector_search_returns_results(api_client, api_test_db):
    """GET /items/search?q=Python&mode=vector uses query embedding and returns vector results."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-src")
        ci_id = insert_content_item(session, src_id, "Python Vector Guide")
        iv_id = insert_item_version(session, ci_id)
        # Use StubModelAdapter to produce the same embedding the API will generate
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("Python")
        insert_chunk(
            session,
            iv_id,
            0,
            "Python vector text",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Python&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_search_without_mode_defaults_to_keyword(api_client, api_test_db):
    """GET /items/search?q=... without mode should still return keyword results."""
    unique = uuid.uuid4().hex[:8]
    title = f"KeywordDefaultTest {unique}"
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, f"kw-default-{unique}")
        ci_id = insert_content_item(session, src_id, title)
        insert_item_version(session, ci_id)
        session.commit()
    engine.dispose()

    response = await api_client.get(
        f"/items/search?q={unique}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == title
    assert data["items"][0]["mode"] == "keyword"


@pytest.mark.asyncio
async def test_invalid_mode_returns_error(api_client):
    """GET /items/search?q=Python&mode=unknown should return 422."""
    response = await api_client.get(
        "/items/search?q=Python&mode=unknown",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_vector_search_rejects_nonzero_offset(api_client):
    """GET /items/search?mode=vector&offset=1 should return 422."""
    response = await api_client.get(
        "/items/search?q=test&mode=vector&offset=1",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 422
    assert "offset is not supported in vector mode" in response.json()["detail"]


@pytest.mark.asyncio
async def test_vector_search_accepts_zero_offset(api_client, api_test_db):
    """GET /items/search?mode=vector&offset=0 should succeed."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-off0-src")
        ci_id = insert_content_item(session, src_id, "Vector Offset Zero")
        iv_id = insert_item_version(session, ci_id)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("OffsetZero")
        insert_chunk(
            session,
            iv_id,
            0,
            "offset zero chunk",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=OffsetZero&mode=vector&offset=0",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_vector_blank_query_returns_empty(api_client):
    """GET /items/search?q=   &mode=vector should return 200 with empty results."""
    response = await api_client.get(
        "/items/search?q=%20%20%20&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_vector_response_contains_expected_fields(api_client, api_test_db):
    """Vector search response must include chunk_id, item_version_id, content_item_id, title, text, distance, mode."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-fields-src")
        ci_id = insert_content_item(session, src_id, "Vector Fields Article")
        iv_id = insert_item_version(session, ci_id)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("Fields")
        insert_chunk(
            session,
            iv_id,
            0,
            "fields chunk text",
            embedding=emb,
            embedding_status="ready",
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Fields&mode=vector",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    required_fields = {
        "chunk_id",
        "item_version_id",
        "content_item_id",
        "title",
        "text",
        "distance",
        "mode",
    }
    assert required_fields.issubset(set(item.keys()))
    assert item["mode"] == "vector"


@pytest.mark.asyncio
async def test_vector_filter_by_source_id(api_client, api_test_db):
    """Vector search with source_id only returns chunks from that source."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_a = insert_source(session, "vec-src-a")
        src_b = insert_source(session, "vec-src-b")
        ci_a = insert_content_item(session, src_a, "Python Source A")
        ci_b = insert_content_item(session, src_b, "Python Source B")
        iv_a = insert_item_version(session, ci_a)
        iv_b = insert_item_version(session, ci_b)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("Python")
        insert_chunk(
            session, iv_a, 0, "source a chunk", embedding=emb, embedding_status="ready"
        )
        insert_chunk(
            session, iv_b, 0, "source b chunk", embedding=emb, embedding_status="ready"
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        f"/items/search?q=Python&mode=vector&source_id={src_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content_item_id"] == str(ci_a)


@pytest.mark.asyncio
async def test_vector_filter_by_topic_watch_id(api_client, api_test_db):
    """Vector search with topic_watch_id only returns chunks from that topic."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-topic-src")
        tw_a = insert_topic(session, "vec-topic-a")
        tw_b = insert_topic(session, "vec-topic-b")
        ci_a = insert_content_item(
            session, src_id, "Python Topic A", topic_watch_id=tw_a
        )
        ci_b = insert_content_item(
            session, src_id, "Python Topic B", topic_watch_id=tw_b
        )
        iv_a = insert_item_version(session, ci_a)
        iv_b = insert_item_version(session, ci_b)
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("Python")
        insert_chunk(
            session, iv_a, 0, "topic a chunk", embedding=emb, embedding_status="ready"
        )
        insert_chunk(
            session, iv_b, 0, "topic b chunk", embedding=emb, embedding_status="ready"
        )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        f"/items/search?q=Python&mode=vector&topic_watch_id={tw_a}",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content_item_id"] == str(ci_a)


@pytest.mark.asyncio
async def test_vector_limit_parameter(api_client, api_test_db):
    """Vector search with limit returns at most that many results."""
    engine = create_engine(api_test_db)
    with Session(bind=engine) as session:
        src_id = insert_source(session, "vec-limit-src")
        from harvester.adapters.stub_model import StubModelAdapter

        adapter = StubModelAdapter()
        emb = adapter.embed("Python")
        for i in range(3):
            ci = insert_content_item(session, src_id, f"Python Limit {i}")
            iv = insert_item_version(session, ci)
            insert_chunk(
                session,
                iv,
                0,
                f"limit chunk {i}",
                embedding=emb,
                embedding_status="ready",
            )
        session.commit()
    engine.dispose()

    response = await api_client.get(
        "/items/search?q=Python&mode=vector&limit=1",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 1
