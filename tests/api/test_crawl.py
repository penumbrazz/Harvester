"""Tests for crawl run API endpoint.

Covers: POST /crawl/run authentication, success response,
source/recipe status rejection, and policy denial.
"""

from __future__ import annotations

import json
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

from harvester.adapters.firecrawl import CrawlResult
from harvester.domain.fetch_policy import FetchPolicyResult, REASON_PRIVATE_IP
from harvester.jobs.archive import ArchiveWriteResult


@pytest.fixture(scope="module")
def api_test_db():
    """Create an isolated test database for crawl API tests."""
    db_name = f"harvester_crawl_test_{uuid.uuid4().hex[:8]}"
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


def _insert_source(db_url: str, *, status="watched", url="https://example.com"):
    source_id = uuid.uuid4()
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
                name=f"crawl-test-source-{source_id.hex[:8]}",
                kind="web",
                url=url,
                status=status,
                trust_level="medium",
                auth_required=False,
                failure_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        )
        session.commit()
    return source_id


def _insert_recipe(db_url: str, *, approval_status="approved", risk_level="low"):
    recipe_id = uuid.uuid4()
    with Session(bind=create_engine(db_url)) as session:
        session.execute(
            sa.text(
                "INSERT INTO recipes "
                "(id, name, executor, config, risk_level, approval_status, version, "
                "created_at, updated_at) VALUES "
                "(:id, :name, :executor, :config, :risk_level, :approval_status, "
                ":version, :created_at, :updated_at)"
            ),
            dict(
                id=recipe_id,
                name=f"crawl-test-recipe-{recipe_id.hex[:8]}",
                executor="firecrawl",
                config=json.dumps({"url_pattern": "*"}),
                risk_level=risk_level,
                approval_status=approval_status,
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        )
        session.commit()
    return recipe_id


def _make_archive_result():
    return ArchiveWriteResult(
        relative_path="2025-01-15/test.raw",
        storage_uri="file:///archive/2025-01-15/test.raw",
        content_hash="sha256:abc123",
        byte_size=100,
        content_type="text/html",
        retention_days=7,
        retain_until=datetime.now(timezone.utc),
    )


class TestCrawlRunAuth:
    """POST /crawl/run requires authentication."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, api_client: AsyncClient):
        response = await api_client.post("/crawl/run", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self, api_client: AsyncClient):
        response = await api_client.post(
            "/crawl/run",
            json={},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401


class TestCrawlRunSuccess:
    """Successful crawl run returns expected fields."""

    @pytest.mark.asyncio
    async def test_successful_crawl_run(self, api_client: AsyncClient, api_test_db):
        source_id = _insert_source(api_test_db)
        recipe_id = _insert_recipe(api_test_db)

        crawl_result = CrawlResult(
            original_url="https://example.com",
            final_url="https://example.com/page",
            status_code=200,
            content_type="text/html",
            payload_text="<html>content</html>",
        )

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.execute_adapter_crawl",
                return_value=crawl_result,
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(),
            ),
        ):
            response = await api_client.post(
                "/crawl/run",
                json={"source_id": str(source_id), "recipe_id": str(recipe_id)},
                headers={"Authorization": "Bearer test-secret"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "crawl_run_id" in data
        assert data["status"] == "completed"
        assert "raw_object_id" in data


class TestCrawlRunRejection:
    """Reject invalid source/recipe states."""

    @pytest.mark.asyncio
    async def test_rejects_missing_source(self, api_client: AsyncClient):
        response = await api_client.post(
            "/crawl/run",
            json={"source_id": str(uuid.uuid4()), "recipe_id": str(uuid.uuid4())},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_invalid_uuid_format(self, api_client: AsyncClient):
        response = await api_client.post(
            "/crawl/run",
            json={"source_id": "not-a-uuid", "recipe_id": "not-a-uuid"},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_candidate_source(self, api_client: AsyncClient, api_test_db):
        source_id = _insert_source(api_test_db, status="candidate")
        recipe_id = _insert_recipe(api_test_db)

        response = await api_client.post(
            "/crawl/run",
            json={"source_id": str(source_id), "recipe_id": str(recipe_id)},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_policy_denial_returns_failed(
        self, api_client: AsyncClient, api_test_db
    ):
        source_id = _insert_source(api_test_db)
        recipe_id = _insert_recipe(api_test_db)

        with patch(
            "harvester.jobs.crawl_execution.check_fetch_policy",
            return_value=FetchPolicyResult(allowed=False, reason=REASON_PRIVATE_IP),
        ):
            response = await api_client.post(
                "/crawl/run",
                json={"source_id": str(source_id), "recipe_id": str(recipe_id)},
                headers={"Authorization": "Bearer test-secret"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None
