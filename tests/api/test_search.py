"""Tests for GET /items/search API endpoint."""

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command


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


def _now() -> datetime:
    return datetime.now(UTC)


def _insert_source(session: Session, name: str | None = None) -> uuid.UUID:
    """Insert a source row and return its id."""
    src_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, created_at, updated_at) "
            "VALUES (:id, :name, 'rss', 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {"id": src_id, "name": name or f"src-{uuid.uuid4().hex[:6]}", "ts": _now()},
    )
    return src_id


def _insert_topic(session: Session, name: str | None = None) -> uuid.UUID:
    """Insert a topic_watch row and return its id."""
    tw_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO topic_watches (id, name, query, status, created_at, updated_at) "
            "VALUES (:id, :name, :query, 'active', :ts, :ts)"
        ),
        {"id": tw_id, "name": name or f"topic-{uuid.uuid4().hex[:6]}", "query": "test", "ts": _now()},
    )
    return tw_id


def _insert_content_item(
    session: Session,
    source_id: uuid.UUID,
    title: str,
    *,
    topic_watch_id: uuid.UUID | None = None,
    canonical_url: str | None = None,
) -> uuid.UUID:
    """Insert a content_item row and return its id."""
    ci_id = uuid.uuid4()
    url = canonical_url or f"https://example.com/{uuid.uuid4().hex[:8]}"
    session.execute(
        sa.text(
            "INSERT INTO content_items "
            "(id, item_type, title, source_id, topic_watch_id, "
            "canonical_url, canonical_url_hash, status, created_at, updated_at) "
            "VALUES (:id, 'article', :title, :source_id, :tw_id, "
            ":url, md5(:url), 'active', :ts, :ts)"
        ),
        {
            "id": ci_id,
            "title": title,
            "source_id": source_id,
            "tw_id": topic_watch_id,
            "url": url,
            "ts": _now(),
        },
    )
    return ci_id


def _insert_item_version(session: Session, content_item_id: uuid.UUID) -> uuid.UUID:
    """Insert an item_version row and return its id."""
    iv_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO item_versions "
            "(id, content_item_id, content_hash, created_at) "
            "VALUES (:id, :ci_id, :hash, :ts)"
        ),
        {"id": iv_id, "ci_id": content_item_id, "hash": uuid.uuid4().hex, "ts": _now()},
    )
    return iv_id


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
        src_id = _insert_source(session, "search-src-1")
        ci_id = _insert_content_item(session, src_id, "Python Async Programming Guide")
        _insert_item_version(session, ci_id)
        ci2_id = _insert_content_item(session, src_id, "Rust Ownership Model")
        _insert_item_version(session, ci2_id)
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
        src_a = _insert_source(session, "filter-src-a")
        src_b = _insert_source(session, "filter-src-b")
        ci_a = _insert_content_item(session, src_a, "Python Data Analysis")
        _insert_item_version(session, ci_a)
        ci_b = _insert_content_item(session, src_b, "Python Web Development")
        _insert_item_version(session, ci_b)
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
        src_id = _insert_source(session, "topic-src")
        tw_a = _insert_topic(session, "topic-a")
        tw_b = _insert_topic(session, "topic-b")
        ci_a = _insert_content_item(session, src_id, "Python ML Guide", topic_watch_id=tw_a)
        _insert_item_version(session, ci_a)
        ci_b = _insert_content_item(session, src_id, "Python DL Guide", topic_watch_id=tw_b)
        _insert_item_version(session, ci_b)
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
        src_id = _insert_source(session, "limit-src")
        for i in range(3):
            ci = _insert_content_item(session, src_id, f"Python Article {i}")
            _insert_item_version(session, ci)
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
        src_id = _insert_source(session, "offset-src")
        for i in range(4):
            ci = _insert_content_item(session, src_id, f"Python Offset {i}")
            _insert_item_version(session, ci)
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
        src_id = _insert_source(session, "fields-src")
        ci_id = _insert_content_item(
            session, src_id, "Field Test Article",
            canonical_url="https://example.com/field-test",
        )
        _insert_item_version(session, ci_id)
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
    expected_fields = {"item_id", "version_id", "source_id", "title", "canonical_url", "created_at"}
    assert set(item.keys()) == expected_fields
    assert item["title"] == "Field Test Article"
    assert item["canonical_url"] == "https://example.com/field-test"
    assert item["source_id"] == str(src_id)
