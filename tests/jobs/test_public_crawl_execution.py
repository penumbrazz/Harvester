"""Tests for crawl execution service.

Covers: approved source/recipe success, unapproved source rejection,
unapproved recipe rejection, high-risk recipe rejection, policy denial,
and adapter failure.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa

from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import CrawlRun, RawObject, Source, Recipe
from harvester.domain.fetch_policy import FetchPolicyResult, REASON_PRIVATE_IP
from harvester.domain.state import CRAWL_RUN_TRANSITIONS
from harvester.jobs.archive import ArchiveConfig, ArchiveWriteResult
from harvester.jobs.crawl_execution import (
    CrawlExecutionError,
    execute_crawl,
)


def _insert_source(db_session, *, status="watched", name=None, url=None, **overrides):
    source_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=source_id,
        name=name or f"test-source-{source_id.hex[:8]}",
        kind="web",
        url=url or "https://example.com",
        status=status,
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    columns = ", ".join(defaults.keys())
    placeholders = ", ".join(f":{k}" for k in defaults.keys())
    db_session.execute(
        sa.text(f"INSERT INTO sources ({columns}) VALUES ({placeholders})"),
        defaults,
    )
    return source_id


def _insert_recipe(db_session, *, approval_status="approved", risk_level="low", **overrides):
    recipe_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=recipe_id,
        name=f"test-recipe-{recipe_id.hex[:8]}",
        executor="firecrawl",
        config=json.dumps({"url_pattern": "*"}),
        risk_level=risk_level,
        approval_status=approval_status,
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    columns = ", ".join(defaults.keys())
    placeholders = ", ".join(f":{k}" for k in defaults.keys())
    db_session.execute(
        sa.text(f"INSERT INTO recipes ({columns}) VALUES ({placeholders})"),
        defaults,
    )
    return recipe_id


def _insert_crawl_run(db_session, source_id, recipe_id, *, status="pending", **overrides):
    run_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=run_id,
        source_id=source_id,
        recipe_id=recipe_id,
        status=status,
        started_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    columns = ", ".join(defaults.keys())
    placeholders = ", ".join(f":{k}" for k in defaults.keys())
    db_session.execute(
        sa.text(f"INSERT INTO crawl_runs ({columns}) VALUES ({placeholders})"),
        defaults,
    )
    return run_id


def _make_archive_result(**overrides):
    defaults = dict(
        relative_path="2025-01-15/test.raw",
        storage_uri="file:///archive/2025-01-15/test.raw",
        content_hash="sha256:abc123",
        byte_size=100,
        content_type="text/html",
        retention_days=7,
        retain_until=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return ArchiveWriteResult(**defaults)


class TestApprovedSourceSuccess:
    """Approved source + approved low-risk recipe should succeed."""

    def test_successful_crawl(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(db_session, approval_status="approved", risk_level="low")
        db_session.commit()

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
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )

        assert result.status == "completed"
        assert result.raw_object_id is not None


class TestUnapprovedSourceRejection:
    """Unapproved or missing sources MUST be rejected."""

    @pytest.mark.parametrize("status", ["candidate", "paused"])
    def test_rejects_non_watched_source(self, db_session, status):
        source_id = _insert_source(db_session, status=status)
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        with pytest.raises(CrawlExecutionError) as exc_info:
            execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert "source" in str(exc_info.value).lower()

    def test_rejects_missing_source(self, db_session):
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        with pytest.raises(CrawlExecutionError):
            execute_crawl(
                session=db_session,
                source_id=uuid.uuid4(),
                recipe_id=recipe_id,
                actor="test",
            )


class TestUnapprovedRecipeRejection:
    """Unapproved recipes MUST be rejected."""

    @pytest.mark.parametrize("approval_status", ["pending", "rejected"])
    def test_rejects_unapproved_recipe(self, db_session, approval_status):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(db_session, approval_status=approval_status)
        db_session.commit()

        with pytest.raises(CrawlExecutionError) as exc_info:
            execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert "recipe" in str(exc_info.value).lower()

    def test_rejects_missing_recipe(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        db_session.commit()

        with pytest.raises(CrawlExecutionError):
            execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=uuid.uuid4(),
                actor="test",
            )


class TestHighRiskRecipeRejection:
    """High-risk recipes MUST be rejected."""

    def test_rejects_high_risk_recipe(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(db_session, approval_status="approved", risk_level="high")
        db_session.commit()

        with pytest.raises(CrawlExecutionError) as exc_info:
            execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert "risk" in str(exc_info.value).lower() or "recipe" in str(
            exc_info.value
        ).lower()


class TestPolicyDenial:
    """Fetch policy denial MUST fail the crawl run."""

    def test_policy_denial_fails_crawl(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(db_session, approval_status="approved", risk_level="low")
        db_session.commit()

        with patch(
            "harvester.jobs.crawl_execution.check_fetch_policy",
            return_value=FetchPolicyResult(allowed=False, reason=REASON_PRIVATE_IP),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert result.status == "failed"
        assert "policy" in result.error_message.lower() or "private" in result.error_message.lower()


class TestAdapterFailure:
    """Adapter errors MUST fail the crawl run."""

    def test_adapter_error_fails_crawl(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(db_session, approval_status="approved", risk_level="low")
        db_session.commit()

        crawl_result = CrawlResult(
            original_url="https://example.com",
            error="Firecrawl returned HTTP 502",
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
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert result.status == "failed"
        assert result.error_message is not None
