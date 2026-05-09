"""Tests for create_job idempotency behavior."""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from harvester.db.models import Job
from harvester.jobs.repository import create_job


class TestCreateJobIdempotency:
    """Tests for idempotent job creation via idempotency_key."""

    def test_same_idempotency_key_no_duplicate(self, db_session):
        """Creating a job with the same idempotency_key should return None."""
        key = f"test-idem-{uuid.uuid4().hex[:8]}"
        payload = {"url": "https://example.com"}

        first = create_job(
            db_session,
            job_type="crawl",
            payload=payload,
            idempotency_key=key,
        )
        assert first is not None
        assert first.idempotency_key == key

        second = create_job(
            db_session,
            job_type="crawl",
            payload=payload,
            idempotency_key=key,
        )
        assert second is None

        # Verify only one job exists with this key
        count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(Job)
            .where(Job.idempotency_key == key)
        )
        assert count == 1

    def test_no_idempotency_key_allows_duplicates(self, db_session):
        """Without idempotency_key, multiple jobs of the same type can exist."""
        first = create_job(
            db_session,
            job_type="crawl",
            payload={"url": "https://example.com"},
        )
        assert first is not None

        second = create_job(
            db_session,
            job_type="crawl",
            payload={"url": "https://example.com"},
        )
        assert second is not None
        assert second.id != first.id

    def test_different_idempotency_keys_create_separate_jobs(self, db_session):
        """Different idempotency keys should create separate jobs."""
        job_a = create_job(
            db_session,
            job_type="crawl",
            idempotency_key="key-alpha",
        )
        job_b = create_job(
            db_session,
            job_type="crawl",
            idempotency_key="key-beta",
        )
        assert job_a is not None
        assert job_b is not None
        assert job_a.id != job_b.id

    def test_idempotency_key_with_custom_priority(self, db_session):
        """Idempotent creation should respect the first call's parameters."""
        key = f"test-prio-{uuid.uuid4().hex[:8]}"

        first = create_job(
            db_session,
            job_type="crawl",
            priority=10,
            idempotency_key=key,
        )
        assert first is not None
        assert first.priority == 10

        # Second call with different priority is still a no-op
        second = create_job(
            db_session,
            job_type="crawl",
            priority=0,
            idempotency_key=key,
        )
        assert second is None

        # Original job keeps its priority
        db_session.reset()
        original = db_session.get(Job, first.id)
        assert original.priority == 10
