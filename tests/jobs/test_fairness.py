"""Tests for job queue fairness — per-source cap, per-job-type cap, protected lanes."""

import uuid
from datetime import datetime, timezone, timedelta

import sqlalchemy as sa

from harvester.db.models import Job
from harvester.jobs.repository import claim_next_jobs, create_job


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
        source_id=None,
        lane=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    db_session.execute(
        sa.text(
            "INSERT INTO jobs "
            "(id, job_type, status, priority, attempts, max_attempts, "
            "created_at, updated_at, run_after, locked_by, locked_until, "
            "source_id, lane) "
            "VALUES "
            "(:id, :job_type, :status, :priority, :attempts, :max_attempts, "
            ":created_at, :updated_at, :run_after, :locked_by, :locked_until, "
            ":source_id, :lane)"
        ),
        defaults,
    )
    return defaults["id"]


def _set_running(db_session, job_id, locked_by="worker", minutes=5):
    """Mark a job as running with a valid lease."""
    future = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    db_session.execute(
        sa.text(
            "UPDATE jobs SET status = 'running', locked_by = :lb, "
            "locked_until = :lu WHERE id = :id"
        ),
        {"id": job_id, "lb": locked_by, "lu": future},
    )


class TestPerSourceCap:
    """Tests for per-source max_in_flight fairness."""

    def test_source_cap_limits_claimed_jobs(self, db_session):
        """Jobs from a source at cap should be skipped."""
        source_a = str(uuid.uuid4())
        source_b = str(uuid.uuid4())

        # Insert 2 running jobs for source_a (cap = 2)
        for _ in range(2):
            jid = _insert_job(db_session, source_id=source_a)
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        # Insert a pending job from source_a (should be skipped)
        blocked_id = _insert_job(db_session, source_id=source_a, priority=10)
        # Insert a pending job from source_b (should be claimed)
        free_id = _insert_job(db_session, source_id=source_b, priority=5)
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=5,
            max_per_source=2,
        )
        claimed_ids = [j.id for j in claimed]
        assert blocked_id not in claimed_ids
        assert free_id in claimed_ids

    def test_different_sources_each_get_slots(self, db_session):
        """Each source gets its own cap allocation."""
        source_a = str(uuid.uuid4())
        source_b = str(uuid.uuid4())

        # 1 running for each source
        for sid in (source_a, source_b):
            jid = _insert_job(db_session, source_id=sid)
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        # 1 pending each, cap = 2
        pa = _insert_job(db_session, source_id=source_a)
        pb = _insert_job(db_session, source_id=source_b)
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=5,
            max_per_source=2,
        )
        claimed_ids = [j.id for j in claimed]
        assert pa in claimed_ids
        assert pb in claimed_ids


class TestPerJobTypeCap:
    """Tests for per-job-type max_in_flight fairness."""

    def test_job_type_cap_limits_claimed_jobs(self, db_session):
        """Jobs of a type at cap should be skipped."""
        # 3 running 'crawl' jobs (cap = 3)
        for _ in range(3):
            jid = _insert_job(db_session, job_type="crawl")
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        # Pending crawl (blocked) and pending extract (free)
        blocked_id = _insert_job(db_session, job_type="crawl", priority=10)
        free_id = _insert_job(db_session, job_type="extract", priority=5)
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=5,
            max_per_job_type=3,
        )
        claimed_ids = [j.id for j in claimed]
        assert blocked_id not in claimed_ids
        assert free_id in claimed_ids


class TestProtectedLanes:
    """Tests for manual/failure lane bypassing caps."""

    def test_manual_lane_bypasses_source_cap(self, db_session):
        """Jobs in the manual lane should bypass per-source caps."""
        source_a = str(uuid.uuid4())

        # Saturate source_a
        for _ in range(5):
            jid = _insert_job(db_session, source_id=source_a)
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        # Manual lane job from same source
        manual_id = _insert_job(
            db_session,
            source_id=source_a,
            lane="manual",
            priority=10,
        )
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=1,
            max_per_source=2,
        )
        assert len(claimed) == 1
        assert claimed[0].id == manual_id

    def test_failure_lane_bypasses_job_type_cap(self, db_session):
        """Jobs in the failure lane should bypass per-job-type caps."""
        # Saturate 'crawl' type
        for _ in range(5):
            jid = _insert_job(db_session, job_type="crawl")
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        # Failure lane job of same type
        failure_id = _insert_job(
            db_session,
            job_type="crawl",
            lane="failure",
            priority=10,
        )
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=1,
            max_per_job_type=3,
        )
        assert len(claimed) == 1
        assert claimed[0].id == failure_id

    def test_normal_job_blocked_when_caps_full(self, db_session):
        """Normal jobs (no lane) are blocked when both caps are saturated."""
        source_a = str(uuid.uuid4())

        # Saturate both caps
        for _ in range(5):
            jid = _insert_job(
                db_session,
                source_id=source_a,
                job_type="crawl",
            )
            db_session.commit()
            _set_running(db_session, jid)
            db_session.commit()

        normal_id = _insert_job(
            db_session,
            source_id=source_a,
            job_type="crawl",
            priority=10,
        )
        db_session.commit()

        claimed = claim_next_jobs(
            db_session,
            "test-worker",
            limit=1,
            max_per_source=2,
            max_per_job_type=3,
        )
        assert all(j.id != normal_id for j in claimed)
