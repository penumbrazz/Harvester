"""Watch scheduler — enqueues crawl jobs for due schedules.

Provides ``run_scheduler_once(session, now, limit)`` which:
1. Queries active schedules where ``next_run_at <= now``.
2. Validates source/topic state.
3. Creates crawl jobs with idempotency keys.
4. Advances ``next_run_at`` on success or duplicate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

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


def run_scheduler_once(
    session: Session,
    *,
    now: datetime,
    limit: int = 100,
) -> SchedulerResult:
    """Scan due schedules and enqueue crawl jobs.

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
        Counts of scanned, enqueued, skipped, and duplicate schedules.
    """
    result = SchedulerResult()

    # Query active schedules that are due
    schedules = (
        session.scalars(
            sa.select(WatchSchedule)
            .where(
                WatchSchedule.status == "active",
                WatchSchedule.next_run_at <= now,
            )
            .order_by(WatchSchedule.next_run_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        .all()
    )

    result.scanned = len(schedules)

    for schedule in schedules:
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

        # Advance schedule regardless of new vs duplicate
        schedule.last_enqueued_at = now
        schedule.next_run_at = now + timedelta(seconds=schedule.interval_seconds)
        session.flush()

    session.commit()
    return result
