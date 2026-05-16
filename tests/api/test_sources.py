"""Tests for source API endpoints."""

import os
import uuid
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for API tests.

    Creates a fresh PostgreSQL database, runs Alembic migrations, and yields
    the connection URL. Drops the database on teardown.
    """
    db_name = f"harvester_api_test_{uuid.uuid4().hex[:8]}"
    admin_url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/postgres"
    test_url = admin_url.rsplit("/", 1)[0] + "/" + db_name

    # Create the database
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    # Run Alembic migrations
    env_backup = os.environ.pop("HARVESTER_DATABASE_URL", None)
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    if env_backup:
        os.environ["HARVESTER_DATABASE_URL"] = env_backup

    yield test_url

    # Cleanup — drop the database
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


@pytest.mark.asyncio
async def test_propose_source_creates_candidate(api_client):
    """POST /sources/propose should create a candidate source."""
    # Arrange & Act
    resp = await api_client.post(
        "/sources/propose",
        json={
            "name": f"test-src-{uuid.uuid4().hex[:6]}",
            "kind": "web",
            "url": "https://example.com",
        },
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "candidate"
    assert "id" in data


@pytest.mark.asyncio
async def test_propose_duplicate_source_returns_409(api_client):
    """POST /sources/propose with duplicate name should return 409."""
    # Arrange
    name = f"dup-{uuid.uuid4().hex[:6]}"
    await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — propose the same name again
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_promote_source(api_client):
    """POST /sources/{id}/promote should transition candidate -> testing."""
    # Arrange
    resp = await api_client.post(
        "/sources/propose",
        json={"name": f"promo-{uuid.uuid4().hex[:6]}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "testing"


@pytest.mark.asyncio
async def test_pause_watched_source(api_client):
    """POST /sources/{id}/pause should transition watched -> paused."""
    # Arrange — create and promote to watched
    name = f"pause-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    # Promote twice: candidate -> testing -> watched
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_promote_nonexistent_source_returns_404(api_client):
    """POST /sources/{id}/promote with invalid id should return 404."""
    # Act
    resp = await api_client.post(
        f"/sources/{uuid.uuid4()}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_transition_persists_rejection_audit(api_client, api_test_db):
    """Illegal transition must persist a rejection audit event."""
    # Arrange — create a candidate source
    resp = await api_client.post(
        "/sources/propose",
        json={"name": f"audit-{uuid.uuid4().hex[:6]}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act — try to pause a candidate (illegal: candidate -> paused is not allowed)
    resp = await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 400

    # Assert — rejection audit must be in the database
    engine = create_engine(api_test_db)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT action FROM audit_events "
                "WHERE entity_id = :eid AND action = 'status_change_rejected'"
            ),
            {"eid": source_id},
        ).fetchone()
    engine.dispose()
    assert row is not None, "Rejection audit event must be persisted after illegal transition"
    assert row[0] == "status_change_rejected"


# ---------------------------------------------------------------------------
# Task 1.1 — GET /sources API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sources_returns_created_sources(api_client):
    """GET /sources should return sources with expected fields."""
    # Arrange — create two sources with unique prefixes
    tag = uuid.uuid4().hex[:6]
    name_a = f"list-a-{tag}"
    name_b = f"list-b-{tag}"
    await api_client.post(
        "/sources/propose",
        json={"name": name_a, "kind": "web", "url": "https://a.example.com"},
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        "/sources/propose",
        json={"name": name_b, "kind": "rss", "url": "https://b.example.com/feed"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.get(
        "/sources",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 2
    names = {s["name"] for s in data["items"]}
    assert name_a in names
    assert name_b in names

    # Verify expected fields are present on our created sources
    our_sources = [s for s in data["items"] if s["name"] in (name_a, name_b)]
    for source in our_sources:
        assert "id" in source
        assert "name" in source
        assert "kind" in source
        assert "status" in source
        assert "url" in source
        assert "trust_level" in source
        assert "failure_count" in source
        assert "created_at" in source
        assert "updated_at" in source


@pytest.mark.asyncio
async def test_list_sources_requires_auth(api_client):
    """GET /sources without authentication should return 401."""
    resp = await api_client.get("/sources")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_sources_sorted_by_created_at_desc(api_client):
    """GET /sources should return sources sorted by created_at descending."""
    # Arrange — create sources in order with unique tag
    tag = uuid.uuid4().hex[:6]
    names = [f"sort-{i}-{tag}" for i in range(3)]
    for name in names:
        await api_client.post(
            "/sources/propose",
            json={"name": name, "kind": "web"},
            headers={"Authorization": "Bearer test-secret"},
        )

    # Act
    resp = await api_client.get(
        "/sources",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — extract our sources and verify newest first
    data = resp.json()
    our_sources = [s for s in data["items"] if s["name"] in names]
    our_sources.sort(key=lambda s: s["created_at"], reverse=True)
    result_names = [s["name"] for s in our_sources]
    assert result_names == list(reversed(names))


# ---------------------------------------------------------------------------
# Task 1.2 — Source status and kind filter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_sources_by_status(api_client):
    """GET /sources?status=candidate should only return candidate sources."""
    # Arrange — create and promote one source to testing
    name_candidate = f"filt-c-{uuid.uuid4().hex[:6]}"
    name_testing = f"filt-t-{uuid.uuid4().hex[:6]}"
    await api_client.post(
        "/sources/propose",
        json={"name": name_candidate, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name_testing, "kind": "rss"},
        headers={"Authorization": "Bearer test-secret"},
    )
    testing_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{testing_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.get(
        "/sources?status=candidate",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — filter returns only candidate sources; ours is included
    assert resp.status_code == 200
    data = resp.json()
    for source in data["items"]:
        assert source["status"] == "candidate"
    our_names = {s["name"] for s in data["items"]}
    assert name_candidate in our_names
    assert name_testing not in our_names


@pytest.mark.asyncio
async def test_filter_sources_by_kind(api_client):
    """GET /sources?kind=rss should only return RSS sources."""
    # Arrange — use unique tag to isolate our sources
    tag = uuid.uuid4().hex[:6]
    name_web = f"filt-web-{tag}"
    name_rss = f"filt-rss-{tag}"
    await api_client.post(
        "/sources/propose",
        json={"name": name_web, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        "/sources/propose",
        json={"name": name_rss, "kind": "rss"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.get(
        "/sources?kind=rss",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — filter returns only rss sources; ours is included
    assert resp.status_code == 200
    data = resp.json()
    for source in data["items"]:
        assert source["kind"] == "rss"
    our_names = {s["name"] for s in data["items"]}
    assert name_rss in our_names
    assert name_web not in our_names


# ---------------------------------------------------------------------------
# Task 1.3 — Resume and archive API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_paused_source(api_client):
    """POST /sources/{id}/resume should transition paused -> watched."""
    # Arrange — create and promote to watched, then pause
    name = f"resume-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — resume
    resp = await api_client.post(
        f"/sources/{source_id}/resume",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "watched"


@pytest.mark.asyncio
async def test_archive_candidate_source(api_client):
    """POST /sources/{id}/archive should transition candidate -> archived."""
    # Arrange
    name = f"archive-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/archive",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_watched_source(api_client):
    """POST /sources/{id}/archive should transition watched -> archived."""
    # Arrange — create and promote to watched
    name = f"arch-w-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    resp = await api_client.post(
        f"/sources/{source_id}/archive",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_resume_non_paused_source_rejected(api_client):
    """POST /sources/{id}/resume on a candidate should return 400."""
    # Arrange
    name = f"resume-rej-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act — try to resume a candidate (illegal)
    resp = await api_client.post(
        f"/sources/{source_id}/resume",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_archive_non_archivable_source_rejected(api_client):
    """POST /sources/{id}/archive on an already archived source should return 400."""
    # Arrange — create and archive
    name = f"arch-rej-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{source_id}/archive",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — try to archive again
    resp = await api_client.post(
        f"/sources/{source_id}/archive",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_writes_audit_event(api_client, api_test_db):
    """Resume transition must write an audit event."""
    # Arrange — create, promote to watched, pause
    name = f"resume-audit-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/promote",
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        f"/sources/{source_id}/pause",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act
    await api_client.post(
        f"/sources/{source_id}/resume",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — audit event for status_change exists
    engine = create_engine(api_test_db)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT after_state FROM audit_events "
                "WHERE entity_id = :eid AND action = 'status_change' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"eid": source_id},
        ).fetchone()
    engine.dispose()
    assert row is not None
    after = row[0] if isinstance(row[0], dict) else __import__("json").loads(row[0])
    assert after.get("status") == "watched"


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sources_default_pagination(api_client):
    """GET /sources should return paginated response with default limit/offset."""
    resp = await api_client.get(
        "/sources",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert isinstance(data["total"], int)
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_sources_custom_pagination(api_client):
    """GET /sources?limit=1&offset=0 should respect pagination params."""
    # Create at least 2 sources
    tag = uuid.uuid4().hex[:6]
    await api_client.post(
        "/sources/propose",
        json={"name": f"page-a-{tag}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    await api_client.post(
        "/sources/propose",
        json={"name": f"page-b-{tag}", "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )

    resp = await api_client.get(
        "/sources?limit=1&offset=0",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert data["total"] >= 2
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_list_sources_offset_beyond_total(api_client):
    """GET /sources with offset beyond total should return empty items."""
    resp = await api_client.get(
        "/sources?limit=20&offset=99999",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_list_sources_invalid_limit(api_client):
    """GET /sources with limit > 100 should return 422."""
    resp = await api_client.get(
        "/sources?limit=200",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_sources_negative_offset(api_client):
    """GET /sources with negative offset should return 422."""
    resp = await api_client.get(
        "/sources?offset=-1",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Task 2 — PATCH /sources/{id} API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_source_updates_fields(api_client, api_test_db):
    """PATCH /sources/{id} should update name, url, trust_level and write audit."""
    # Arrange — create a candidate source
    tag = uuid.uuid4().hex[:6]
    resp = await api_client.post(
        "/sources/propose",
        json={
            "name": f"patch-{tag}",
            "kind": "web",
            "url": "https://old.example.com",
            "trust_level": "low",
        },
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]

    # Act — patch with new values
    new_name = f"patched-{tag}"
    resp = await api_client.patch(
        f"/sources/{source_id}",
        json={
            "name": new_name,
            "url": "https://new.example.com",
            "trust_level": "high",
        },
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert — response reflects updated fields
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == new_name
    assert data["url"] == "https://new.example.com"
    assert data["trust_level"] == "high"

    # Assert — audit event with action='source.update' exists
    engine = create_engine(api_test_db)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT action, after_state FROM audit_events "
                "WHERE entity_id = :eid AND action = 'source.update' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"eid": source_id},
        ).fetchone()
    engine.dispose()
    assert row is not None, "Update audit event must be persisted after PATCH"
    assert row[0] == "source.update"
    after = row[1] if isinstance(row[1], dict) else __import__("json").loads(row[1])
    assert after.get("name") == new_name
    assert after.get("url") == "https://new.example.com"
    assert after.get("trust_level") == "high"


@pytest.mark.asyncio
async def test_patch_archived_source_rejected(api_client):
    """PATCH /sources/{id} on an archived source should return 400."""
    # Arrange — create and archive a source
    name = f"patch-arch-{uuid.uuid4().hex[:6]}"
    resp = await api_client.post(
        "/sources/propose",
        json={"name": name, "kind": "web"},
        headers={"Authorization": "Bearer test-secret"},
    )
    source_id = resp.json()["id"]
    await api_client.post(
        f"/sources/{source_id}/archive",
        headers={"Authorization": "Bearer test-secret"},
    )

    # Act — try to patch the archived source
    resp = await api_client.patch(
        f"/sources/{source_id}",
        json={"name": f"should-not-work-{uuid.uuid4().hex[:6]}"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Assert
    assert resp.status_code == 400
