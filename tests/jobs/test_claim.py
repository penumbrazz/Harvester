"""Tests for job claim mechanics with FOR UPDATE SKIP LOCKED."""

import uuid
from datetime import datetime, timezone, timedelta

import sqlalchemy as sa

from harvester.db.models import Job
from harvester.jobs.repository import claim_next_jobs


def _insert_job(db_session, **overrides):
    """Helper to insert a job directly via SQL."""
    defaults = dict(
        id=uuid.uuid4(),
        job_type="crawl",
        status="pending",
        priority=0,
        attempts=0,
        max_attempts=3,
        run_after=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    db_session.execute(
        sa.text(
            "INSERT INTO jobs "
            "(id, job_type, status, priority, attempts, max_attempts, "
            "created_at, updated_at, run_after) "
            "VALUES "
            "(:id, :job_type, :status, :priority, :attempts, :max_attempts, "
            ":created_at, :updated_at, :run_after)"
        ),
        defaults,
    )
    return defaults["id"]


class TestClaimNextJobs:
    """Tests for the claim_next_jobs function."""

    def test_claim_pending_job(self, db_session):
        """Should claim a pending job and set it to running."""
        job_id = _insert_job(db_session, id=uuid.uuid4())
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) >= 1

        # Verify the job is now locked and running
        result = db_session.execute(
            sa.text("SELECT locked_by, status FROM jobs WHERE id = :id"),
            {"id": job_id},
        )
        row = result.fetchone()
        assert row[0] == "worker-1"
        assert row[1] == "running"

    def test_same_job_not_claimed_twice(self, db_session):
        """Two sequential claims should not return the same job."""
        job_id = _insert_job(db_session, id=uuid.uuid4())
        db_session.commit()

        # First claim takes the job
        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) >= 1

        # Second claim should not get the same job
        claimed2 = claim_next_jobs(db_session, "worker-2", limit=1)
        assert all(c.id != job_id for c in claimed2)

    def test_respects_priority_order(self, db_session):
        """Higher priority jobs should be claimed first."""
        low_id = _insert_job(db_session, id=uuid.uuid4(), priority=0)
        high_id = _insert_job(db_session, id=uuid.uuid4(), priority=10)
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) == 1
        assert claimed[0].priority == 10
        assert claimed[0].id == high_id

    def test_filters_by_lanes(self, db_session):
        """Should only claim jobs of specified types when lanes is set."""
        crawl_id = _insert_job(db_session, id=uuid.uuid4(), job_type="crawl")
        embed_id = _insert_job(db_session, id=uuid.uuid4(), job_type="embed")
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=10, lanes=["crawl"])
        assert len(claimed) >= 1
        assert all(j.job_type == "crawl" for j in claimed)

    def test_skips_future_jobs(self, db_session):
        """Should not claim jobs with run_after in the future."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _insert_job(db_session, id=uuid.uuid4(), run_after=future)
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) == 0

    def test_claims_ready_job_with_past_run_after(self, db_session):
        """Should claim a job whose run_after is in the past."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        job_id = _insert_job(db_session, id=uuid.uuid4(), run_after=past)
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) == 1
        assert claimed[0].id == job_id

    def test_claims_multiple_jobs_up_to_limit(self, db_session):
        """Should claim up to `limit` jobs when available."""
        for _ in range(5):
            _insert_job(db_session, id=uuid.uuid4())
        db_session.commit()

        claimed = claim_next_jobs(db_session, "worker-1", limit=3)
        assert len(claimed) == 3

    def test_returns_empty_when_no_pending_jobs(self, db_session):
        """Should return an empty list when no pending jobs exist."""
        claimed = claim_next_jobs(db_session, "worker-1", limit=5)
        assert claimed == []
