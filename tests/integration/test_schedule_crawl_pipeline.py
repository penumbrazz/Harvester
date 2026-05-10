"""Integration test: schedule -> scheduler enqueue -> crawl worker -> raw_object.

End-to-end test verifying the complete watch-scheduler-crawl-worker pipeline:
1. Create source, recipe, and watch schedule
2. Run scheduler to enqueue crawl job
3. Process crawl job via crawl worker
4. Verify raw_object and crawl_run are created and traceable
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy import text

from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import CrawlRun, Job, RawObject
from harvester.domain.fetch_policy import FetchPolicyResult
from harvester.jobs.archive import ArchiveWriteResult
from harvester.jobs.scheduler import run_scheduler_once
from harvester.workers.crawl import process_crawl_job


def _insert_source(session) -> uuid.UUID:
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO sources "
            "(id, name, kind, url, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'web', :url, 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {
            "id": sid,
            "name": f"int_src_{sid.hex[:8]}",
            "url": "https://example.com",
            "ts": now,
        },
    )
    return sid


def _insert_recipe(session) -> uuid.UUID:
    rid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": rid, "name": f"int_recipe_{rid.hex[:8]}", "ts": now},
    )
    return rid


def _insert_schedule(
    session,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    interval_seconds: int = 3600,
) -> uuid.UUID:
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    key = f"source:{source_id}:recipe:{recipe_id}"
    session.execute(
        text(
            "INSERT INTO watch_schedules "
            "(id, schedule_key, source_id, recipe_id, status, "
            "interval_seconds, next_run_at, priority, created_at, updated_at) "
            "VALUES (:id, :key, :src, :recipe, 'active', "
            ":interval, :next_run, 0, :ts, :ts)"
        ),
        {
            "id": sid,
            "key": key,
            "src": source_id,
            "recipe": recipe_id,
            "interval": interval_seconds,
            "next_run": now - timedelta(hours=1),
            "ts": now,
        },
    )
    return sid


class TestScheduleCrawlPipeline:
    """Full pipeline integration test."""

    @patch("harvester.jobs.crawl_execution.write_archive")
    @patch("harvester.jobs.crawl_execution.execute_adapter_crawl")
    @patch("harvester.jobs.crawl_execution.check_fetch_policy")
    def test_schedule_to_raw_object(
        self, mock_policy, mock_adapter, mock_archive, db_session
    ):
        """Full pipeline: schedule -> scheduler -> crawl worker -> raw_object."""
        # Step 1: Set up source, recipe, schedule
        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        schedule_id = _insert_schedule(db_session, source_id, recipe_id)
        db_session.commit()

        # Step 2: Run scheduler to enqueue crawl job
        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)
        assert result.scanned == 1
        assert result.enqueued == 1

        # Verify crawl job was created
        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 1
        crawl_job = jobs[0]
        assert crawl_job.payload["source_id"] == str(source_id)
        assert crawl_job.payload["recipe_id"] == str(recipe_id)

        # Claim the job (simulate worker claiming)
        from harvester.jobs.repository import claim_next_jobs

        claimed = claim_next_jobs(
            db_session, "test-worker", limit=1, lanes=["crawl"]
        )
        assert len(claimed) == 1
        claimed_job = claimed[0]

        # Step 3: Configure mocks for successful crawl
        mock_policy.return_value = FetchPolicyResult(allowed=True)
        mock_adapter.return_value = CrawlResult(
            original_url="https://example.com",
            status_code=200,
            payload_text="<html>integration test content</html>",
            content_type="text/html",
            final_url="https://example.com",
            error=None,
        )
        mock_archive.return_value = ArchiveWriteResult(
            relative_path="2026/01/int_test.raw",
            storage_uri="file:///tmp/int_test.raw",
            content_hash="int_hash_123",
            content_type="text/html",
            byte_size=200,
            retention_days=7,
            retain_until=now + timedelta(days=7),
        )

        # Step 4: Process crawl job
        success = process_crawl_job(db_session, claimed_job)
        assert success is True

        # Step 5: Verify traceability
        # - CrawlRun should exist and be completed
        crawl_runs = db_session.query(CrawlRun).all()
        assert len(crawl_runs) == 1
        assert crawl_runs[0].status == "completed"
        assert crawl_runs[0].source_id == source_id

        # - RawObject should exist
        raw_objects = db_session.query(RawObject).all()
        assert len(raw_objects) == 1
        assert raw_objects[0].source_id == source_id
        assert raw_objects[0].content_hash == "int_hash_123"

        # - CrawlRun should reference the RawObject
        assert crawl_runs[0].raw_object_id == raw_objects[0].id

        # - Schedule should have advanced
        from harvester.db.models import WatchSchedule

        schedule = db_session.get(WatchSchedule, schedule_id)
        assert schedule.next_run_at > now
        assert schedule.last_enqueued_at is not None
