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
from harvester.db.models import CrawlRun, CrawlTarget, RawObject, Source, Recipe
from harvester.domain.fetch_policy import FetchPolicyResult, REASON_PRIVATE_IP
from harvester.domain.state import CRAWL_RUN_TRANSITIONS
from harvester.jobs.archive import ArchiveConfig, ArchiveWriteResult
from harvester.jobs.crawl_execution import (
    CrawlExecutionError,
    execute_crawl,
)
from harvester.jobs.crawl_targets import upsert_crawl_target


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


def _insert_recipe(
    db_session, *, approval_status="approved", risk_level="low", **overrides
):
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


def _insert_crawl_run(
    db_session, source_id, recipe_id, *, status="pending", **overrides
):
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
        recipe_id = _insert_recipe(
            db_session, approval_status="approved", risk_level="low"
        )
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

    def test_successful_target_crawl_uses_target_url_and_updates_target(
        self, db_session
    ):
        source_id = _insert_source(
            db_session,
            status="watched",
            url="https://www.chinacdc.cn/jksj/jksj04_14249/",
        )
        recipe_id = _insert_recipe(
            db_session,
            approval_status="approved",
            risk_level="low",
        )
        db_session.commit()
        target, _ = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            target_role="detail",
            media_type="html",
            depth=1,
        )
        db_session.commit()

        crawl_result = CrawlResult(
            original_url=target.target_url,
            final_url=target.target_url,
            status_code=200,
            content_type="text/html",
            payload_text="<html>target content</html>",
        )

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ) as mock_policy,
            patch(
                "harvester.jobs.crawl_execution.execute_adapter_crawl",
                return_value=crawl_result,
            ) as mock_adapter,
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        assert result.status == "completed"
        mock_adapter.assert_called_once_with(target.target_url)
        assert mock_policy.call_args_list[0].args[0] == target.target_url
        updated = db_session.get(CrawlTarget, target.id)
        assert updated.status == "completed"
        assert updated.last_raw_object_id == result.raw_object_id
        assert updated.final_url == target.target_url


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
        recipe_id = _insert_recipe(
            db_session, approval_status="approved", risk_level="high"
        )
        db_session.commit()

        with pytest.raises(CrawlExecutionError) as exc_info:
            execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="test",
            )
        assert (
            "risk" in str(exc_info.value).lower()
            or "recipe" in str(exc_info.value).lower()
        )


class TestPolicyDenial:
    """Fetch policy denial MUST fail the crawl run."""

    def test_policy_denial_fails_crawl(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(
            db_session, approval_status="approved", risk_level="low"
        )
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
        assert (
            "policy" in result.error_message.lower()
            or "private" in result.error_message.lower()
        )


class TestTargetCrawlFailures:
    """Target crawl failures should update target diagnostics."""

    def _seed_target(self, db_session):
        source_id = _insert_source(
            db_session,
            status="watched",
            url="https://www.chinacdc.cn/jksj/jksj04_14249/",
        )
        recipe_id = _insert_recipe(
            db_session,
            approval_status="approved",
            risk_level="low",
        )
        db_session.commit()
        target, _ = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            target_role="detail",
            media_type="html",
            depth=1,
        )
        db_session.commit()
        return source_id, recipe_id, target

    def test_policy_denial_fails_target(self, db_session):
        """Fetch policy denial should mark target failed without raw object."""
        source_id, recipe_id, target = self._seed_target(db_session)

        with patch(
            "harvester.jobs.crawl_execution.check_fetch_policy",
            return_value=FetchPolicyResult(allowed=False, reason=REASON_PRIVATE_IP),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                target_id=target.id,
                actor="test",
            )

        updated = db_session.get(CrawlTarget, target.id)
        assert result.status == "failed"
        assert updated.status == "failed"
        assert updated.failure_count == 1
        assert "policy" in updated.last_error.lower()
        assert updated.last_raw_object_id is None

    def test_redirect_denial_fails_target(self, db_session):
        """Redirect policy denial should mark target failed."""
        source_id, recipe_id, target = self._seed_target(db_session)
        crawl_result = CrawlResult(
            original_url=target.target_url,
            final_url="http://127.0.0.1/private",
            status_code=302,
            content_type="text/html",
            payload_text="redirected",
        )

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                side_effect=[
                    FetchPolicyResult(allowed=True),
                    FetchPolicyResult(allowed=False, reason=REASON_PRIVATE_IP),
                ],
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
                target_id=target.id,
                actor="test",
            )

        updated = db_session.get(CrawlTarget, target.id)
        assert result.status == "failed"
        assert updated.status == "failed"
        assert updated.failure_count == 1
        assert "redirect" in updated.last_error.lower()

    def test_adapter_error_fails_target_and_remains_retryable(self, db_session):
        """Adapter errors should mark target failed and stay retryable."""
        source_id, recipe_id, target = self._seed_target(db_session)
        crawl_result = CrawlResult(
            original_url=target.target_url,
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
            with pytest.raises(CrawlExecutionError) as exc_info:
                execute_crawl(
                    session=db_session,
                    source_id=source_id,
                    recipe_id=recipe_id,
                    target_id=target.id,
                    actor="test",
                )

        updated = db_session.get(CrawlTarget, target.id)
        assert exc_info.value.retryable is True
        assert updated.status == "failed"
        assert updated.failure_count == 1
        assert "502" in updated.last_error


class TestAdapterFailure:
    """Adapter errors MUST fail the crawl run."""

    def test_adapter_error_fails_crawl(self, db_session):
        source_id = _insert_source(db_session, status="watched")
        recipe_id = _insert_recipe(
            db_session, approval_status="approved", risk_level="low"
        )
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
            with pytest.raises(CrawlExecutionError) as exc_info:
                execute_crawl(
                    session=db_session,
                    source_id=source_id,
                    recipe_id=recipe_id,
                    actor="test",
                )
        assert exc_info.value.retryable is True
        assert "502" in str(exc_info.value)
