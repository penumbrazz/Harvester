"""Tests for lease expiry recovery and job retry logic."""

import uuid
from datetime import datetime, timezone, timedelta

import sqlalchemy as sa

from harvester.db.models import Job
from harvester.jobs.repository import claim_next_jobs, fail_job, create_job


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
        locked_by=None,
        locked_until=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    db_session.execute(
        sa.text(
            "INSERT INTO jobs "
            "(id, job_type, status, priority, attempts, max_attempts, "
            "created_at, updated_at, run_after, locked_by, locked_until) "
            "VALUES "
            "(:id, :job_type, :status, :priority, :attempts, :max_attempts, "
            ":created_at, :updated_at, :run_after, :locked_by, :locked_until)"
        ),
        defaults,
    )
    return defaults["id"]


def _set_job_status(db_session, job_id, status, locked_by=None, locked_until=None):
    """Helper to directly update a job's status and lock fields."""
    db_session.execute(
        sa.text(
            "UPDATE jobs SET status = :status, locked_by = :locked_by, "
            "locked_until = :locked_until WHERE id = :id"
        ),
        {
            "id": job_id,
            "status": status,
            "locked_by": locked_by,
            "locked_until": locked_until,
        },
    )


class TestLeaseExpiry:
    """Tests for expired lease recovery."""

    def test_expired_lease_can_be_reclaimed(self, db_session):
        """A job with an expired lease should be claimable again."""
        job_id = _insert_job(db_session, id=uuid.uuid4())
        db_session.commit()

        # Simulate a worker claiming the job with an expired lease
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        _set_job_status(db_session, job_id, "running", "old-worker", past)
        db_session.commit()

        # claim_next_jobs should automatically recover expired leases
        claimed = claim_next_jobs(db_session, "new-worker", limit=1)
        assert len(claimed) >= 1
        assert claimed[0].id == job_id
        assert claimed[0].status == "running"
        assert claimed[0].locked_by == "new-worker"

    def test_running_job_with_valid_lease_not_reclaimed(self, db_session):
        """A running job with a valid lease should not be claimed again."""
        job_id = _insert_job(db_session, id=uuid.uuid4())
        db_session.commit()

        # Set a valid future lease
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        _set_job_status(db_session, job_id, "running", "active-worker", future)
        db_session.commit()

        # Pending-only filter should not pick this up
        claimed = claim_next_jobs(db_session, "other-worker", limit=1)
        assert all(c.id != job_id for c in claimed)


class TestRetryMechanism:
    """Tests for failed job retry and dead-letter behavior."""

    def test_failed_job_creates_retry_when_under_max_attempts(self, db_session):
        """A failed job with attempts < max_attempts should create a retry job."""
        job_id = _insert_job(db_session, id=uuid.uuid4(), attempts=0, max_attempts=3)
        db_session.commit()

        # Claim the job first so it is in running state
        claimed = claim_next_jobs(db_session, "worker-1", limit=1)
        assert len(claimed) >= 1

        fail_job(db_session, job_id, "transient error")

        # Original job should be failed
        original = db_session.get(Job, job_id)
        assert original.status == "failed"
        assert original.attempts == 1
        assert original.last_error == "transient error"

        # A retry job should exist in pending state
        retry_jobs = db_session.scalars(
            sa.select(Job).where(
                Job.status == "pending",
                Job.job_type == "crawl",
                Job.id != job_id,
            )
        ).all()
        assert len(retry_jobs) >= 1

    def test_retry_job_has_backoff_delay(self, db_session):
        """Retry jobs should have a run_after set in the future."""
        job_id = _insert_job(db_session, id=uuid.uuid4(), attempts=0, max_attempts=3)
        db_session.commit()

        claim_next_jobs(db_session, "worker-1", limit=1)
        fail_job(db_session, job_id, "error")

        retry_job = db_session.scalar(
            sa.select(Job).where(
                Job.status == "pending",
                Job.id != job_id,
            )
        )
        assert retry_job is not None
        assert retry_job.run_after is not None
        assert retry_job.run_after > datetime.now(timezone.utc)

    def test_retry_job_has_lower_priority(self, db_session):
        """Retry jobs should have lower priority than the original."""
        job_id = _insert_job(
            db_session, id=uuid.uuid4(), priority=5, attempts=0, max_attempts=3
        )
        db_session.commit()

        claim_next_jobs(db_session, "worker-1", limit=1)
        fail_job(db_session, job_id, "error")

        retry_job = db_session.scalar(
            sa.select(Job).where(
                Job.status == "pending",
                Job.id != job_id,
            )
        )
        assert retry_job is not None
        assert retry_job.priority < 5

    def test_exhausted_job_becomes_dead_letter(self, db_session):
        """A job that has exhausted max_attempts should become 'dead'."""
        job_id = _insert_job(db_session, id=uuid.uuid4(), attempts=2, max_attempts=3)
        db_session.commit()

        claim_next_jobs(db_session, "worker-1", limit=1)
        fail_job(db_session, job_id, "permanent failure")

        # Original should be dead, not failed
        original = db_session.get(Job, job_id)
        assert original.status == "dead"
        assert original.attempts == 3
        assert original.last_error == "permanent failure"

        # No retry job should be created
        retry_jobs = db_session.scalars(
            sa.select(Job).where(
                Job.status == "pending",
                Job.id != job_id,
            )
        ).all()
        assert len(retry_jobs) == 0
