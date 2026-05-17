"""Tests for the crawl job handler — process_crawl_job.

Covers: successful crawl, missing payload, missing source/recipe,
unapproved recipe, fetch policy permanent failure, adapter retryable failure,
and topic_watch_id propagation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import sqlalchemy as sa

from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import CrawlRun, Job
from harvester.domain.fetch_policy import REASON_PRIVATE_IP, FetchPolicyResult
from harvester.jobs.archive import ArchiveWriteResult
from harvester.workers.crawl import process_crawl_job


def _insert_source(db_session, *, status="watched", url="https://example.com"):
    source_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, url, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'web', :url, :status, 'medium', false, 0, :ts, :ts)"
        ),
        {
            "id": source_id,
            "name": f"crawl-src-{source_id.hex[:8]}",
            "url": url,
            "status": status,
            "ts": datetime.now(UTC),
        },
    )
    return source_id


def _insert_recipe(
    db_session,
    *,
    approval_status="approved",
    risk_level="low",
):
    recipe_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', :risk, :approval, 1, :ts, :ts)"
        ),
        {
            "id": recipe_id,
            "name": f"crawl-recipe-{recipe_id.hex[:8]}",
            "risk": risk_level,
            "approval": approval_status,
            "ts": datetime.now(UTC),
        },
    )
    return recipe_id


def _make_crawl_job(
    db_session,
    *,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    topic_watch_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    job_type: str = "crawl",
):
    """Create a pending crawl job for testing."""
    job = Job(
        id=uuid.uuid4(),
        job_type=job_type,
        status="running",
        payload={
            "source_id": str(source_id),
            "recipe_id": str(recipe_id),
            **({"topic_watch_id": str(topic_watch_id)} if topic_watch_id else {}),
            **({"target_id": str(target_id)} if target_id else {}),
        },
    )
    db_session.add(job)
    db_session.flush()
    return job


class TestCrawlHandlerSuccess:
    """Test successful crawl job processing."""

    @patch("harvester.jobs.crawl_execution.write_archive")
    @patch("harvester.jobs.crawl_execution.execute_adapter_crawl")
    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_successful_crawl_completes_job(
        self, mock_policy, mock_adapter, mock_archive, db_session
    ):
        """Successful crawl should complete the job and create a CrawlRun."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)
        mock_adapter.return_value = CrawlResult(
            original_url="https://example.com",
            status_code=200,
            payload_text="<html>content</html>",
            content_type="text/html",
            final_url="https://example.com",
            error=None,
        )
        mock_archive.return_value = ArchiveWriteResult(
            relative_path="2026/01/test.raw",
            storage_uri="file:///tmp/test.raw",
            content_hash="abc123",
            content_type="text/html",
            byte_size=100,
            retention_days=7,
            retain_until=datetime.now(UTC),
        )

        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        job = _make_crawl_job(db_session, source_id=source_id, recipe_id=recipe_id)

        result = process_crawl_job(db_session, job)
        assert result is True

        # Job should be completed
        db_session.expire(job, ["status"])
        assert job.status == "completed"

        # CrawlRun should exist
        crawl_runs = db_session.query(CrawlRun).all()
        assert len(crawl_runs) == 1
        assert crawl_runs[0].status == "completed"

    @patch("harvester.workers.crawl.execute_crawl")
    def test_target_id_payload_passed_to_crawl_service(self, mock_execute, db_session):
        """Crawl jobs with target_id should pass it to execute_crawl."""
        mock_execute.return_value = MagicMock(status="completed")
        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        target_id = uuid.uuid4()
        job = _make_crawl_job(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_id=target_id,
        )

        result = process_crawl_job(db_session, job)

        assert result is True
        mock_execute.assert_called_once()
        assert mock_execute.call_args.kwargs["target_id"] == target_id


class TestCrawlHandlerPermanentErrors:
    """Test permanent error handling — no retry."""

    def test_missing_payload_dead_letters(self, db_session):
        """Missing payload should dead-letter the job."""
        job = Job(
            id=uuid.uuid4(),
            job_type="crawl",
            status="running",
            payload=None,
        )
        db_session.add(job)
        db_session.flush()

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    def test_missing_source_id_in_payload_dead_letters(self, db_session):
        """Missing source_id in payload should dead-letter the job."""
        job = Job(
            id=uuid.uuid4(),
            job_type="crawl",
            status="running",
            payload={"recipe_id": str(uuid.uuid4())},
        )
        db_session.add(job)
        db_session.flush()

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    def test_missing_recipe_id_in_payload_dead_letters(self, db_session):
        """Missing recipe_id in payload should dead-letter the job."""
        job = Job(
            id=uuid.uuid4(),
            job_type="crawl",
            status="running",
            payload={"source_id": str(uuid.uuid4())},
        )
        db_session.add(job)
        db_session.flush()

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_missing_source_dead_letters(self, mock_policy, db_session):
        """Non-existent source should dead-letter the job."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)

        recipe_id = _insert_recipe(db_session)
        job = _make_crawl_job(
            db_session,
            source_id=uuid.uuid4(),
            recipe_id=recipe_id,
        )

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_missing_recipe_dead_letters(self, mock_policy, db_session):
        """Non-existent recipe should dead-letter the job."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)

        source_id = _insert_source(db_session)
        job = _make_crawl_job(
            db_session,
            source_id=source_id,
            recipe_id=uuid.uuid4(),
        )

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_unapproved_recipe_dead_letters(self, mock_policy, db_session):
        """Unapproved recipe should dead-letter the job."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)

        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session, approval_status="pending")
        job = _make_crawl_job(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
        )

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"

    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_fetch_policy_denied_dead_letters(self, mock_policy, db_session):
        """Fetch policy denial should dead-letter the job."""
        mock_policy.return_value = FetchPolicyResult(
            allowed=False, reason=REASON_PRIVATE_IP
        )

        source_id = _insert_source(db_session, url="https://192.168.1.1")
        recipe_id = _insert_recipe(db_session)
        job = _make_crawl_job(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
        )

        result = process_crawl_job(db_session, job)
        assert result is False

        db_session.expire(job, ["status"])
        assert job.status == "dead"


class TestCrawlHandlerRetryableErrors:
    """Test retryable error handling — fail_job for retry."""

    @patch("harvester.jobs.crawl_execution.write_archive")
    @patch("harvester.jobs.crawl_execution.execute_adapter_crawl")
    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_adapter_failure_retries(
        self, mock_policy, mock_adapter, mock_archive, db_session
    ):
        """Adapter error should trigger fail_job for retry."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)
        mock_adapter.side_effect = Exception("Connection timeout")

        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        job = _make_crawl_job(db_session, source_id=source_id, recipe_id=recipe_id)

        result = process_crawl_job(db_session, job)
        assert result is False

        # Original job should be failed (not dead)
        db_session.expire(job, ["status"])
        assert job.status == "failed"


class TestCrawlHandlerTopicWatchId:
    """Test that topic_watch_id is propagated to CrawlRun."""

    @patch("harvester.jobs.crawl_execution.write_archive")
    @patch("harvester.jobs.crawl_execution.execute_adapter_crawl")
    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_topic_watch_id_propagated_to_crawl_run(
        self, mock_policy, mock_adapter, mock_archive, db_session
    ):
        """topic_watch_id from payload should be written to CrawlRun."""
        mock_policy.return_value = FetchPolicyResult(allowed=True)
        mock_adapter.return_value = CrawlResult(
            original_url="https://example.com",
            status_code=200,
            payload_text="<html>content</html>",
            content_type="text/html",
            final_url="https://example.com",
            error=None,
        )
        mock_archive.return_value = ArchiveWriteResult(
            relative_path="2026/01/test.raw",
            storage_uri="file:///tmp/test.raw",
            content_hash="abc123",
            content_type="text/html",
            byte_size=100,
            retention_days=7,
            retain_until=datetime.now(UTC),
        )

        # Create topic watch
        topic_id = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO topic_watches "
                "(id, name, status, created_at, updated_at) "
                "VALUES (:id, :name, 'active', :ts, :ts)"
            ),
            {
                "id": topic_id,
                "name": f"topic_{topic_id.hex[:8]}",
                "ts": datetime.now(UTC),
            },
        )

        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        job = _make_crawl_job(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            topic_watch_id=topic_id,
        )

        result = process_crawl_job(db_session, job)
        assert result is True

        crawl_runs = db_session.query(CrawlRun).all()
        assert len(crawl_runs) == 1
        assert crawl_runs[0].topic_watch_id == topic_id
