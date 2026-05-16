"""Tests for crawl target API endpoints.

Covers: list targets with filters, target fields, failed targets in failures view.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for crawl target API tests."""
    db_name = f"harvester_target_api_{uuid.uuid4().hex[:8]}"
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


def _insert_source_and_recipe(db_url: str):
    """Insert a source and recipe, return (source_id, recipe_id)."""
    source_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with Session(bind=create_engine(db_url)) as session:
        session.execute(
            sa.text(
                "INSERT INTO sources "
                "(id, name, kind, url, status, trust_level, auth_required, failure_count, "
                "created_at, updated_at) VALUES "
                "(:id, :name, :kind, :url, :status, :trust_level, :auth_required, "
                ":failure_count, :created_at, :updated_at)"
            ),
            dict(
                id=source_id,
                name=f"src-{source_id.hex[:8]}",
                kind="web",
                url="https://example.com/list",
                status="watched",
                trust_level="medium",
                auth_required=False,
                failure_count=0,
                created_at=now,
                updated_at=now,
            ),
        )
        session.execute(
            sa.text(
                "INSERT INTO recipes "
                "(id, name, executor, config, risk_level, approval_status, version, "
                "created_at, updated_at) VALUES "
                "(:id, :name, :executor, :config, :risk_level, :approval_status, :version, "
                ":created_at, :updated_at)"
            ),
            dict(
                id=recipe_id,
                name=f"recipe-{recipe_id.hex[:8]}",
                executor="firecrawl",
                config='{"discovery": {"enabled": true}}',
                risk_level="low",
                approval_status="approved",
                version=1,
                created_at=now,
                updated_at=now,
            ),
        )
        session.commit()
    return source_id, recipe_id


def _insert_crawl_target(
    db_url: str,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    *,
    target_url="https://example.com/detail/1.html",
    target_role="detail",
    media_type="html",
    status="pending",
    depth=0,
    failure_count=0,
    last_error=None,
):
    """Insert a crawl target row, return its id."""
    target_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    import hashlib

    canonical_url = target_url
    canonical_url_hash = hashlib.sha256(canonical_url.encode()).hexdigest()
    with Session(bind=create_engine(db_url)) as session:
        session.execute(
            sa.text(
                "INSERT INTO crawl_targets "
                "(id, source_id, recipe_id, target_url, canonical_url, canonical_url_hash, "
                "target_role, media_type, status, depth, priority, failure_count, last_error, "
                "first_seen_at, last_seen_at, created_at, updated_at) VALUES "
                "(:id, :source_id, :recipe_id, :target_url, :canonical_url, :canonical_url_hash, "
                ":target_role, :media_type, :status, :depth, 0, :failure_count, :last_error, "
                ":now, :now, :now, :now)"
            ),
            dict(
                id=target_id,
                source_id=source_id,
                recipe_id=recipe_id,
                target_url=target_url,
                canonical_url=canonical_url,
                canonical_url_hash=canonical_url_hash,
                target_role=target_role,
                media_type=media_type,
                status=status,
                depth=depth,
                failure_count=failure_count,
                last_error=last_error,
                now=now,
            ),
        )
        session.commit()
    return target_id


@pytest.mark.asyncio
async def test_targets_requires_auth(api_client):
    """GET /crawl/targets should require API token."""
    resp = await api_client.get("/crawl/targets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_targets_returns_empty(api_client):
    """GET /crawl/targets should return empty list when no targets exist."""
    resp = await api_client.get(
        "/crawl/targets",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_targets_returns_items(api_client, api_test_db):
    """GET /crawl/targets should return crawl target records."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(api_test_db, source_id, recipe_id)

    resp = await api_client.get(
        "/crawl/targets",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "id" in item
    assert "source_id" in item
    assert "target_url" in item
    assert "target_role" in item
    assert "media_type" in item
    assert "status" in item
    assert "depth" in item
    assert "failure_count" in item
    assert "last_error" in item
    assert "first_seen_at" in item
    assert "last_seen_at" in item


@pytest.mark.asyncio
async def test_targets_does_not_expose_raw_payload_fields(api_client, api_test_db):
    """Target response should NOT include raw payload or storage fields."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(api_test_db, source_id, recipe_id)

    resp = await api_client.get(
        "/crawl/targets",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    item = data["items"][0]
    assert "last_raw_object_id" not in item
    assert "discovered_from_raw_object_id" not in item
    assert "parent_target_id" not in item
    assert "canonical_url_hash" not in item


@pytest.mark.asyncio
async def test_targets_source_filter(api_client, api_test_db):
    """GET /crawl/targets?source_id=X should filter by source."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(api_test_db, source_id, recipe_id)

    resp = await api_client.get(
        f"/crawl/targets?source_id={source_id}",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["source_id"] == str(source_id) for item in data["items"])


@pytest.mark.asyncio
async def test_targets_role_filter(api_client, api_test_db):
    """GET /crawl/targets?target_role=detail should filter by role."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(
        api_test_db,
        source_id,
        recipe_id,
        target_role="detail",
        target_url="https://example.com/detail.html",
    )
    _insert_crawl_target(
        api_test_db,
        source_id,
        recipe_id,
        target_role="asset",
        media_type="pdf",
        target_url="https://example.com/report.pdf",
    )

    resp = await api_client.get(
        "/crawl/targets?target_role=detail",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["target_role"] == "detail" for item in data["items"])


@pytest.mark.asyncio
async def test_targets_status_filter(api_client, api_test_db):
    """GET /crawl/targets?status=failed should filter by status."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(
        api_test_db,
        source_id,
        recipe_id,
        status="completed",
        target_url="https://example.com/ok.html",
    )
    _insert_crawl_target(
        api_test_db,
        source_id,
        recipe_id,
        status="failed",
        target_url="https://example.com/fail.html",
        failure_count=3,
        last_error="connection timeout",
    )

    resp = await api_client.get(
        "/crawl/targets?status=failed",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "failed" for item in data["items"])
    failed_item = data["items"][0]
    assert failed_item["failure_count"] == 3
    assert failed_item["last_error"] == "connection timeout"


@pytest.mark.asyncio
async def test_targets_pagination(api_client, api_test_db):
    """GET /crawl/targets should support limit/offset pagination."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    for i in range(5):
        _insert_crawl_target(
            api_test_db,
            source_id,
            recipe_id,
            target_url=f"https://example.com/page/{i}.html",
        )

    resp = await api_client.get(
        "/crawl/targets?limit=2&offset=0",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5
    assert data["limit"] == 2
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_failures_includes_targets(api_client, api_test_db):
    """GET /failures/recent should include failed crawl targets."""
    source_id, recipe_id = _insert_source_and_recipe(api_test_db)
    _insert_crawl_target(
        api_test_db,
        source_id,
        recipe_id,
        status="failed",
        target_url="https://example.com/broken.pdf",
        media_type="pdf",
        target_role="asset",
        failure_count=2,
        last_error="download failed",
    )

    resp = await api_client.get(
        "/failures/recent",
        headers={"Authorization": "Bearer test-secret"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "targets" in data
    assert len(data["targets"]) >= 1
    target = data["targets"][0]
    assert target["status"] == "failed"
    assert target["target_role"] == "asset"
    assert target["media_type"] == "pdf"
    assert target["last_error"] == "download failed"
    assert "target_url" in target
    assert "failure_count" in target
