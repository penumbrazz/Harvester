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
    *,
    max_per_source: int = 5,
    max_per_job_type: int = 10,
    protected_lanes: list[str] | None = None,
) -> list[Job]:
    """Atomically claim up to *limit* pending jobs for *worker_id*.

    Uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so that multiple workers can
    safely consume from the same queue without blocking each other.

    Implements fairness: per-source cap, per-job-type cap, and a protected
    lane for manual / failure jobs that are always served first.

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
    max_per_source : int
        Max in-flight jobs per source_id. Jobs from saturated sources are
        skipped.
    max_per_job_type : int
        Max in-flight jobs per job_type. Jobs from saturated types are
        skipped.
    protected_lanes : list[str] or None
        Lane values that bypass per-source and per-type caps. Defaults to
        ``["manual", "failure"]``.

    Returns
    -------
    list[Job]
        The claimed job instances (already flushed to the session).
    """
    now = datetime.datetime.now(datetime.UTC)
    lock_until = now + _LOCK_DURATION

    # Reset expired running jobs back to pending so they can be reclaimed.
    expired = (
        sa.select(Job.id)
        .where(
            Job.status == "running",
            Job.locked_until.is_not(None),
            Job.locked_until < now,
        )
        .with_for_update(skip_locked=True)
    )
    expired_ids = [row[0] for row in session.execute(expired).fetchall()]
    if expired_ids:
        session.execute(
            sa.update(Job)
            .where(Job.id.in_(expired_ids))
            .values(status="pending", locked_by=None, locked_until=None)
        )
        session.flush()

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

    if protected_lanes is None:
        protected_lanes = ["manual", "failure"]

    rows = session.scalars(stmt).all()

    # Count current in-flight jobs per source and per job_type.
    in_flight = session.execute(
        sa.select(Job.source_id, Job.job_type, sa.func.count())
        .where(Job.status == "running")
        .group_by(Job.source_id, Job.job_type)
    ).fetchall()

    source_in_flight: dict[str | None, int] = {}
    type_in_flight: dict[str, int] = {}
    for sid, jtype, cnt in in_flight:
        source_in_flight[sid] = source_in_flight.get(sid, 0) + cnt
        type_in_flight[jtype] = type_in_flight.get(jtype, 0) + cnt

    claimed: list[Job] = []
    for job in rows:
        is_protected = job.lane in protected_lanes if job.lane else False
        if not is_protected:
            src = job.source_id
            if src is not None and source_in_flight.get(src, 0) >= max_per_source:
                continue
            if type_in_flight.get(job.job_type, 0) >= max_per_job_type:
                continue

        job.status = "running"
        job.locked_by = worker_id
        job.locked_until = lock_until
        claimed.append(job)

        # Update counters for subsequent fairness checks.
        if job.source_id is not None:
            source_in_flight[job.source_id] = source_in_flight.get(job.source_id, 0) + 1
        type_in_flight[job.job_type] = type_in_flight.get(job.job_type, 0) + 1

        if len(claimed) >= limit:
            break

    session.flush()
    return claimed


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

    job.last_error = error_message
    job.locked_by = None
    job.locked_until = None
    job.attempts += 1

    # Schedule a retry if we haven't exhausted max_attempts.
    if job.attempts < job.max_attempts:
        job.status = "failed"
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
            attempts=job.attempts,
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
        job.status = "dead"
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
    auto_commit: bool = True,
    source_id: str | None = None,
    lane: str | None = None,
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
    auto_commit : bool
        If ``True`` (default), commit the session after creation.
        Set to ``False`` when the caller manages the transaction boundary
        (e.g. pipeline creating downstream jobs in the same transaction).
    source_id : str or None
        Optional source identifier for per-source fairness caps.
    lane : str or None
        Optional lane tag (e.g. ``"manual"``, ``"failure"``) for protected queues.

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
        source_id=source_id,
        lane=lane,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    session.add(job)
    if auto_commit:
        session.commit()
    else:
        session.flush()
    return job
