"""Job database operations — claim, complete, fail, and create jobs."""

from __future__ import annotations

import datetime
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Job

logger = logging.getLogger(__name__)

_LOCK_DURATION = datetime.timedelta(minutes=5)

# Exponential backoff base delay (seconds) for retry jobs.
_BACKOFF_BASE_SECONDS = 60


def claim_next_jobs(
    session: Session,
    worker_id: str,
    limit: int = 1,
    lanes: list[str] | None = None,
) -> list[Job]:
    """Atomically claim up to *limit* pending jobs for *worker_id*.

    Uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so that multiple workers can
    safely consume from the same queue without blocking each other.

    Parameters
    ----------
    session : Session
        Active database session.
    worker_id : str
        Unique identifier of the claiming worker.
    limit : int
        Maximum number of jobs to claim.
    lanes : list[str] or None
        If provided, only jobs whose ``job_type`` is in this list will be
        considered.

    Returns
    -------
    list[Job]
        The claimed job instances (already flushed to the session).
    """
    now = datetime.datetime.now(datetime.UTC)
    lock_until = now + _LOCK_DURATION

    # Build the core query: pending jobs that are ready to run.
    stmt = (
        sa.select(Job)
        .where(
            Job.status == "pending",
            sa.or_(Job.run_after.is_(None), Job.run_after <= now),
        )
        .order_by(Job.priority.desc(), Job.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )

    # Filter by job_type lanes if provided.
    if lanes:
        stmt = stmt.where(Job.job_type.in_(lanes))

    rows = session.scalars(stmt).all()

    for job in rows:
        job.status = "running"
        job.locked_by = worker_id
        job.locked_until = lock_until

    session.flush()
    return list(rows)


def complete_job(
    session: Session,
    job_id: uuid.UUID,
    result: dict | None = None,
) -> None:
    """Mark a job as completed and release its lock.

    Parameters
    ----------
    session : Session
        Active database session.
    job_id : uuid.UUID
        The job to complete.
    result : dict or None
        Optional result payload to attach to the job.
    """
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    job.status = "completed"
    job.locked_by = None
    job.locked_until = None
    if result is not None:
        job.payload = result

    session.commit()


def fail_job(
    session: Session,
    job_id: uuid.UUID,
    error_message: str,
) -> None:
    """Mark a job as failed and optionally schedule a retry.

    If the current attempt count is still below ``max_attempts``, a new retry
    job is created with exponential backoff.  Otherwise the job stays in
    ``failed`` status (dead letter).

    Parameters
    ----------
    session : Session
        Active database session.
    job_id : uuid.UUID
        The job that failed.
    error_message : str
        Human-readable error description.
    """
    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    job.status = "failed"
    job.last_error = error_message
    job.locked_by = None
    job.locked_until = None
    job.attempts += 1

    # Schedule a retry if we haven't exhausted max_attempts.
    if job.attempts < job.max_attempts:
        backoff = _BACKOFF_BASE_SECONDS * (2 ** (job.attempts - 1))
        run_after = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=backoff
        )
        # Lower priority for retry jobs so fresh jobs get served first.
        retry_priority = max(job.priority - 1, -10)

        retry_job = Job(
            id=uuid.uuid4(),
            job_type=job.job_type,
            status="pending",
            priority=retry_priority,
            run_after=run_after,
            payload=job.payload,
            attempts=0,
            max_attempts=job.max_attempts,
            created_at=datetime.datetime.now(datetime.UTC),
        )
        session.add(retry_job)
        logger.info(
            "Scheduled retry job %s for failed job %s (attempt %d/%d, backoff %ds)",
            retry_job.id,
            job.id,
            job.attempts,
            job.max_attempts,
            backoff,
        )
    else:
        logger.warning(
            "Job %s dead-lettered after %d attempts: %s",
            job.id,
            job.attempts,
            error_message,
        )

    session.commit()


def create_job(
    session: Session,
    job_type: str,
    payload: dict | None = None,
    idempotency_key: str | None = None,
    priority: int = 0,
    run_after: datetime.datetime | None = None,
) -> Job | None:
    """Create a new job, skipping if *idempotency_key* already exists.

    Parameters
    ----------
    session : Session
        Active database session.
    job_type : str
        The type of job (e.g. ``"crawl"``, ``"extract"``, ``"embed_chunks"``).
    payload : dict or None
        Arbitrary JSONB payload for the job.
    idempotency_key : str or None
        If provided and a job with this key already exists, the function
        returns ``None`` without creating a duplicate.
    priority : int
        Higher priority jobs are claimed first.
    run_after : datetime or None
        Earliest time the job may be claimed.

    Returns
    -------
    Job or None
        The newly created job, or ``None`` if the idempotency key already
        existed.
    """
    if idempotency_key is not None:
        existing = session.scalar(
            sa.select(Job.id).where(Job.idempotency_key == idempotency_key)
        )
        if existing is not None:
            logger.debug(
                "Skipping job creation — idempotency key %s already exists",
                idempotency_key,
            )
            return None

    job = Job(
        id=uuid.uuid4(),
        job_type=job_type,
        status="pending",
        priority=priority,
        run_after=run_after,
        idempotency_key=idempotency_key,
        payload=payload,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    session.add(job)
    session.commit()
    return job
