"""Tests for watch schedule API endpoints — creation, validation, and auth."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for schedule API tests."""
    db_name = f"harvester_sched_test_{uuid.uuid4().hex[:8]}"
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


def _insert_source(db_url: str) -> str:
    """Insert a watched source and return its id as string."""
    engine = create_engine(db_url)
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO sources "
                "(id, name, kind, status, trust_level, auth_required, failure_count, "
                "created_at, updated_at) "
                "VALUES (:id, :name, 'rss', 'watched', 'medium', false, 0, :ts, :ts)"
            ),
            {"id": sid, "name": f"src_{sid.hex[:8]}", "ts": now},
        )
        conn.commit()
    engine.dispose()
    return str(sid)


def _insert_active_source(db_url: str) -> str:
    """Insert an active source and return its id as string."""
    engine = create_engine(db_url)
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO sources "
                "(id, name, kind, status, trust_level, auth_required, failure_count, "
                "created_at, updated_at) "
                "VALUES (:id, :name, 'rss', 'active', 'medium', false, 0, :ts, :ts)"
            ),
            {"id": sid, "name": f"src_active_{sid.hex[:8]}", "ts": now},
        )
        conn.commit()
    engine.dispose()
    return str(sid)


def _insert_recipe(db_url: str, approval_status: str = "approved") -> str:
    """Insert a recipe and return its id as string."""
    engine = create_engine(db_url)
    rid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes "
                "(id, name, executor, risk_level, approval_status, version, "
                "created_at, updated_at) "
                "VALUES (:id, :name, 'firecrawl', 'low', :status, 1, :ts, :ts)"
            ),
            {"id": rid, "name": f"recipe_{rid.hex[:8]}", "status": approval_status, "ts": now},
        )
        conn.commit()
    engine.dispose()
    return str(rid)


def _insert_topic(db_url: str, status: str = "active", ttl: int | None = None) -> str:
    """Insert a topic watch and return its id as string."""
    engine = create_engine(db_url)
    tid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl) if ttl else None
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO topic_watches "
                "(id, name, status, ttl_seconds, expires_at, created_at, updated_at) "
                "VALUES (:id, :name, :status, :ttl, :expires, :ts, :ts)"
            ),
            {
                "id": tid,
                "name": f"topic_{tid.hex[:8]}",
                "status": status,
                "ttl": ttl,
                "expires": expires_at,
                "ts": now,
            },
        )
        conn.commit()
    engine.dispose()
    return str(tid)


def _insert_topic_source(db_url: str, topic_id: str, source_id: str) -> None:
    """Link a source to a topic via topic_sources."""
    engine = create_engine(db_url)
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO topic_sources "
                "(id, topic_watch_id, source_id, created_at) "
                "VALUES (:id, :topic_id, :source_id, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "topic_id": topic_id,
                "source_id": source_id,
                "ts": now,
            },
        )
        conn.commit()
    engine.dispose()


@pytest.mark.asyncio
async def test_create_source_schedule(api_client, api_test_db):
    """POST /schedules should create a source-only schedule."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == src_id
    assert data["recipe_id"] == recipe_id
    assert data["status"] == "active"
    assert data["interval_seconds"] == 3600
    assert "id" in data
    assert "next_run_at" in data


@pytest.mark.asyncio
async def test_create_topic_source_schedule(api_client, api_test_db):
    """POST /schedules with topic_watch_id creates a topic-source schedule."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)
    topic_id = _insert_topic(api_test_db)
    _insert_topic_source(api_test_db, topic_id, src_id)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "topic_watch_id": topic_id,
            "recipe_id": recipe_id,
            "interval_seconds": 1800,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["topic_watch_id"] == topic_id
    assert data["interval_seconds"] == 1800


@pytest.mark.asyncio
async def test_duplicate_schedule_rejected(api_client, api_test_db):
    """Duplicate schedule_key (same source + recipe) should be rejected."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)

    payload = {
        "source_id": src_id,
        "recipe_id": recipe_id,
        "interval_seconds": 3600,
    }
    headers = {"Authorization": "Bearer test-secret"}

    resp1 = await api_client.post("/schedules", json=payload, headers=headers)
    assert resp1.status_code == 201

    resp2 = await api_client.post("/schedules", json=payload, headers=headers)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_unapproved_recipe_rejected(api_client, api_test_db):
    """Unapproved recipe should be rejected."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db, approval_status="pending")

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_source_rejected(api_client, api_test_db):
    """Non-existent source should return 404."""
    recipe_id = _insert_recipe(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": str(uuid.uuid4()),
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_recipe_rejected(api_client, api_test_db):
    """Non-existent recipe should return 404."""
    src_id = _insert_source(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "recipe_id": str(uuid.uuid4()),
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_topic_rejected(api_client, api_test_db):
    """Non-existent topic should return 404."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "topic_watch_id": str(uuid.uuid4()),
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_topic_source_not_linked_rejected(api_client, api_test_db):
    """Source not attached to topic should be rejected with 422."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)
    topic_id = _insert_topic(api_test_db)
    # Do NOT call _insert_topic_source — source is not linked to topic

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "topic_watch_id": topic_id,
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 422
    assert "not attached" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_auth_required(api_client, api_test_db):
    """Schedule creation requires API token."""
    src_id = _insert_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_active_source_accepted(api_client, api_test_db):
    """Active source (not just watched) should also be accepted."""
    src_id = _insert_active_source(api_test_db)
    recipe_id = _insert_recipe(api_test_db)

    resp = await api_client.post(
        "/schedules",
        json={
            "source_id": src_id,
            "recipe_id": recipe_id,
            "interval_seconds": 3600,
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 201
