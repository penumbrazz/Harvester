"""Watch scheduler — enqueues crawl jobs for due schedules.

Provides ``run_scheduler_once(session, now, limit)`` which:
1. Queries active schedules where ``next_run_at <= now``.
2. Validates source/topic state.
3. Creates crawl jobs with idempotency keys.
4. Advances ``next_run_at`` on success or duplicate.

Also provides ``run_scheduler_loop(session_factory, poll_interval, limit, should_stop)``
for long-running daemon mode.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Source, TopicWatch, WatchSchedule
from harvester.jobs.repository import create_job

logger = logging.getLogger(__name__)


@dataclass
class SchedulerResult:
    """Statistics returned by run_scheduler_once."""

    scanned: int = 0
    enqueued: int = 0
    skipped: int = 0
    duplicates: int = 0
    errors: int = 0


def _fast_forward_next_run_at(
    next_run_at: datetime,
    interval_seconds: int,
    now: datetime,
) -> datetime:
    """Advance *next_run_at* to the next future slot on the interval grid.

    When the schedule missed multiple windows the result snaps forward by
    whole multiples of *interval_seconds* so it lands strictly past *now*
    while staying aligned to the original grid.
    """
    if next_run_at > now:
        return next_run_at

    overdue = (now - next_run_at).total_seconds()
    # floor(overdue / interval) + 1 is the smallest integer whose
    # product with interval exceeds overdue, guaranteeing > now.
    skip = int(overdue // interval_seconds) + 1
    return next_run_at + timedelta(seconds=skip * interval_seconds)


def run_scheduler_once(
    session: Session,
    *,
    now: datetime,
    limit: int = 100,
) -> SchedulerResult:
    """Scan due schedules and enqueue crawl jobs.

    Each schedule is processed inside a savepoint so that a transient
    error on one schedule does not roll back the entire batch.

    Parameters
    ----------
    session : Session
        Active database session.
    now : datetime
        Current time for comparing ``next_run_at``.
    limit : int
        Maximum number of schedules to process in one pass.

    Returns
    -------
    SchedulerResult
        Counts of scanned, enqueued, skipped, duplicate, and errored schedules.
    """
    result = SchedulerResult()

    # Query active schedules that are due
    schedules = session.scalars(
        sa.select(WatchSchedule)
        .where(
            WatchSchedule.status == "active",
            WatchSchedule.next_run_at <= now,
        )
        .order_by(WatchSchedule.next_run_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()

    result.scanned = len(schedules)

    for schedule in schedules:
        # Each schedule gets its own savepoint so a failure only rolls
        # back that one schedule's changes, not the whole batch.
        savepoint = session.begin_nested()
        try:
            # Validate source still exists and is active/watched
            source = session.get(Source, schedule.source_id)
            if source is None or source.status not in ("watched", "active"):
                logger.info(
                    "Pausing schedule %s: source %s not found or inactive",
                    schedule.id,
                    schedule.source_id,
                )
                schedule.status = "paused"
                schedule.updated_at = now
                result.skipped += 1
                session.flush()
                savepoint.commit()
                continue

            # If topic_watch_id is set, validate topic is active and not expired
            if schedule.topic_watch_id:
                topic = session.get(TopicWatch, schedule.topic_watch_id)
                if topic is None or topic.status != "active":
                    logger.info(
                        "Pausing schedule %s: topic %s inactive",
                        schedule.id,
                        schedule.topic_watch_id,
                    )
                    schedule.status = "paused"
                    schedule.updated_at = now
                    result.skipped += 1
                    session.flush()
                    savepoint.commit()
                    continue
                if topic.expires_at and topic.expires_at <= now:
                    logger.info(
                        "Pausing schedule %s: topic %s expired",
                        schedule.id,
                        schedule.topic_watch_id,
                    )
                    schedule.status = "paused"
                    schedule.updated_at = now
                    result.skipped += 1
                    session.flush()
                    savepoint.commit()
                    continue

            # Build idempotency key using schedule id and window start
            window_start = schedule.next_run_at.isoformat()
            idem_key = f"crawl:{schedule.id}:{window_start}"

            # Build job payload
            payload: dict = {
                "source_id": str(schedule.source_id),
                "recipe_id": str(schedule.recipe_id),
                "schedule_id": str(schedule.id),
                "window_start": window_start,
            }
            if schedule.topic_watch_id:
                payload["topic_watch_id"] = str(schedule.topic_watch_id)

            job = create_job(
                session,
                job_type="crawl",
                payload=payload,
                idempotency_key=idem_key,
                priority=schedule.priority,
                source_id=str(schedule.source_id),
                lane=schedule.lane,
                auto_commit=False,
            )

            if job is not None:
                result.enqueued += 1
                logger.info(
                    "Enqueued crawl job %s for schedule %s",
                    job.id,
                    schedule.id,
                )
            else:
                result.duplicates += 1
                logger.info(
                    "Duplicate crawl job for schedule %s window %s",
                    schedule.id,
                    window_start,
                )

            # Fast-forward next_run_at to the next future slot
            schedule.last_enqueued_at = now
            schedule.next_run_at = _fast_forward_next_run_at(
                schedule.next_run_at, schedule.interval_seconds, now
            )
            session.flush()
            savepoint.commit()

        except Exception as exc:
            logger.error("Error processing schedule %s: %s", schedule.id, exc)
            result.errors += 1
            savepoint.rollback()

    session.commit()
    return result


DEFAULT_CLEANUP_INTERVAL_HOURS = 24

_last_cleanup_at: datetime | None = None


def _should_run_cleanup(now: datetime) -> bool:
    """Check if enough time has passed since the last audit cleanup."""
    global _last_cleanup_at
    if _last_cleanup_at is None:
        return True
    interval_hours = int(
        os.environ.get(
            "HARVESTER_AUDIT_CLEANUP_INTERVAL_HOURS",
            str(DEFAULT_CLEANUP_INTERVAL_HOURS),
        )
    )
    return (now - _last_cleanup_at) >= timedelta(hours=interval_hours)


def _run_audit_cleanup(sess: Session, *, now: datetime) -> None:
    """Run audit cleanup with error isolation."""
    from harvester.domain.audit_retention import cleanup_audit_events

    try:
        cr = cleanup_audit_events(sess, now=now)
        sess.commit()
        logger.info(
            "Scheduler daemon audit cleanup: deleted=%d cutoff=%s retention=%dd",
            cr.deleted_count,
            cr.cutoff.isoformat(),
            cr.retention_days,
        )
    except Exception as exc:
        logger.error("Scheduler daemon audit cleanup failed: %s", exc)
        try:
            sess.rollback()
        except Exception:
            logger.exception("Failed to rollback after audit cleanup error")


def run_scheduler_loop(
    session_factory: Callable[[], Session],
    *,
    poll_interval: int = 5,
    limit: int = 100,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Run the scheduler in a loop for daemon mode.

    Each iteration creates a new session, calls ``run_scheduler_once``,
    closes the session, and sleeps if nothing was scanned.

    Audit cleanup runs at a throttled interval (default 24h) within the
    scheduler loop, not as a separate process.

    Parameters
    ----------
    session_factory : Callable
        Factory that returns a new Session per iteration.
    poll_interval : int
        Seconds to sleep when no schedules are scanned.
    limit : int
        Max schedules to process per iteration.
    should_stop : Callable or None
        Optional callable that returns True to stop the loop.
    """
    global _last_cleanup_at

    while True:
        if should_stop and should_stop():
            logger.info("Scheduler daemon stop condition met, exiting loop")
            break

        sess: Session | None = None
        result: SchedulerResult | None = None
        try:
            sess = session_factory()
            now = datetime.now(tz=UTC)
            result = run_scheduler_once(sess, now=now, limit=limit)
            logger.info(
                "Scheduler daemon round complete: "
                "scanned=%d enqueued=%d skipped=%d duplicates=%d errors=%d",
                result.scanned,
                result.enqueued,
                result.skipped,
                result.duplicates,
                result.errors,
            )

            # Throttled audit cleanup
            if _should_run_cleanup(now):
                _run_audit_cleanup(sess, now=now)
                _last_cleanup_at = now
        except Exception as exc:
            logger.error("Scheduler daemon round failed: %s", exc)
            if sess is not None:
                try:
                    sess.rollback()
                except Exception:
                    logger.exception("Failed to rollback after scheduler error")
            time.sleep(poll_interval)
        finally:
            if sess is not None:
                sess.close()

        if result is not None and result.scanned == 0:
            logger.debug(
                "Scheduler daemon: no schedules scanned, sleeping %ds",
                poll_interval,
            )
            time.sleep(poll_interval)

        if should_stop and should_stop():
            logger.info(
                "Scheduler daemon stop condition met after iteration, exiting loop"
            )
            break
