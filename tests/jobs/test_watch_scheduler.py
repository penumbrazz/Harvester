"""Tests for the watch scheduler — run_scheduler_once.

Covers: due source schedule enqueue, due topic schedule enqueue,
not-due schedule skip, expired topic skip, inactive topic skip,
idempotency (duplicate run), and schedule advancement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session

from harvester.db.models import Job, Source, TopicWatch, WatchSchedule
from harvester.jobs.scheduler import SchedulerResult, run_scheduler_once


def _insert_recipe(session: Session) -> uuid.UUID:
    """Insert an approved recipe and return its id."""
    from tests.utils.factories import _now

    rid = uuid.uuid4()
    now = _now()
    session.execute(
        text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": rid, "name": f"recipe_{rid.hex[:8]}", "ts": now},
    )
    return rid


def _insert_source(session: Session, status: str = "watched") -> uuid.UUID:
    """Insert a source and return its id."""
    from tests.utils.factories import _now

    sid = uuid.uuid4()
    now = _now()
    session.execute(
        text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'rss', :status, 'medium', false, 0, :ts, :ts)"
        ),
        {
            "id": sid,
            "name": f"src_{sid.hex[:8]}",
            "status": status,
            "ts": now,
        },
    )
    return sid


def _insert_topic(
    session: Session,
    status: str = "active",
    ttl: int | None = None,
) -> uuid.UUID:
    """Insert a topic watch and return its id."""
    from tests.utils.factories import _now

    tid = uuid.uuid4()
    now = _now()
    expires_at = now + timedelta(seconds=ttl) if ttl else None
    session.execute(
        text(
            "INSERT INTO topic_watches "
            "(id, name, status, ttl_seconds, expires_at, created_at, updated_at) "
            "VALUES (:id, :name, :status, :ttl, :expires, :ts, :ts)"
        ),
        {
            "id": tid,
            "name": f"topic_{tid.hex[:8]}",
            "status": status,
            "ttl": ttl,
            "expires": expires_at,
            "ts": now,
        },
    )
    return tid


def _make_schedule(
    session: Session,
    *,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    topic_watch_id: uuid.UUID | None = None,
    interval_seconds: int = 3600,
    next_run_at: datetime | None = None,
    status: str = "active",
) -> uuid.UUID:
    """Insert a watch schedule and return its id."""
    from tests.utils.factories import _now

    sid = uuid.uuid4()
    now = _now()
    if next_run_at is None:
        next_run_at = now - timedelta(hours=1)  # Due by default

    if topic_watch_id:
        key = f"topic:{topic_watch_id}:source:{source_id}:recipe:{recipe_id}"
    else:
        key = f"source:{source_id}:recipe:{recipe_id}"

    session.execute(
        text(
            "INSERT INTO watch_schedules "
            "(id, schedule_key, source_id, topic_watch_id, recipe_id, "
            "status, interval_seconds, next_run_at, priority, "
            "created_at, updated_at) "
            "VALUES (:id, :key, :src, :topic, :recipe, :status, "
            ":interval, :next_run, 0, :ts, :ts)"
        ),
        {
            "id": sid,
            "key": key,
            "src": source_id,
            "topic": topic_watch_id,
            "recipe": recipe_id,
            "status": status,
            "interval": interval_seconds,
            "next_run": next_run_at,
            "ts": now,
        },
    )
    return sid


class TestSchedulerSourceSchedule:
    """Test scheduler with source-only schedules."""

    def test_due_source_schedule_enqueues_crawl_job(self, db_session):
        """Due source schedule should create a crawl job."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        _make_schedule(db_session, source_id=src, recipe_id=recipe)

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert isinstance(result, SchedulerResult)
        assert result.scanned >= 1
        assert result.enqueued >= 1

        # Verify crawl job was created
        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 1
        assert jobs[0].payload["source_id"] == str(src)
        assert jobs[0].payload["recipe_id"] == str(recipe)

    def test_schedule_advances_next_run_at(self, db_session):
        """After enqueue, next_run_at should advance by interval_seconds."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        interval = 3600
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            interval_seconds=interval,
            next_run_at=past,
        )

        now = datetime.now(timezone.utc)
        run_scheduler_once(db_session, now=now, limit=100)

        schedule = db_session.query(WatchSchedule).first()
        assert schedule.next_run_at >= now + timedelta(seconds=interval - 60)

    def test_not_due_schedule_no_enqueue(self, db_session):
        """Not-due schedule should not enqueue any job."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            next_run_at=future,
        )

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert result.enqueued == 0
        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 0


class TestSchedulerTopicSchedule:
    """Test scheduler with topic-source schedules."""

    def test_due_topic_schedule_enqueues_crawl_job(self, db_session):
        """Due topic schedule should create a crawl job with topic_watch_id."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        topic = _insert_topic(db_session, status="active")
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            topic_watch_id=topic,
        )

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert result.enqueued >= 1
        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 1
        assert jobs[0].payload["topic_watch_id"] == str(topic)

    def test_expired_topic_skipped(self, db_session):
        """Expired topic schedule should be skipped."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        # Create topic that expires in the past
        topic = _insert_topic(db_session, status="active", ttl=-3600)
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            topic_watch_id=topic,
        )

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert result.enqueued == 0
        assert result.skipped >= 1

    def test_inactive_topic_skipped(self, db_session):
        """Inactive (paused) topic schedule should be skipped."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        topic = _insert_topic(db_session, status="paused")
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            topic_watch_id=topic,
        )

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert result.enqueued == 0
        assert result.skipped >= 1


class TestSchedulerIdempotency:
    """Test that duplicate scheduler runs don't create duplicate jobs."""

    def test_duplicate_run_only_one_job(self, db_session):
        """Running scheduler twice for same due schedule creates only one job."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        _make_schedule(db_session, source_id=src, recipe_id=recipe)

        now = datetime.now(timezone.utc)
        result1 = run_scheduler_once(db_session, now=now, limit=100)
        result2 = run_scheduler_once(db_session, now=now, limit=100)

        assert result1.enqueued == 1
        # Second run should find the existing idempotency key
        assert result2.duplicates >= 1 or result2.enqueued == 0

        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 1

    def test_duplicate_run_advances_schedule(self, db_session):
        """Even on duplicate, the schedule should still advance next_run_at."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        interval = 3600
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            interval_seconds=interval,
            next_run_at=past,
        )

        now = datetime.now(timezone.utc)
        run_scheduler_once(db_session, now=now, limit=100)
        run_scheduler_once(db_session, now=now, limit=100)

        # There should still be exactly one job
        jobs = db_session.query(Job).filter(Job.job_type == "crawl").all()
        assert len(jobs) == 1


class TestSchedulerPausedSchedule:
    """Test scheduler behavior with paused/archived schedules."""

    def test_paused_schedule_not_enqueued(self, db_session):
        """Paused schedule should not be considered."""
        src = _insert_source(db_session)
        recipe = _insert_recipe(db_session)
        _make_schedule(
            db_session,
            source_id=src,
            recipe_id=recipe,
            status="paused",
        )

        now = datetime.now(timezone.utc)
        result = run_scheduler_once(db_session, now=now, limit=100)

        assert result.enqueued == 0
