"""Crawl job handler — processes a single crawl job.

Distinguishes permanent errors (dead-letter) from retryable errors (fail_job).
Permanent errors: missing payload, missing source/recipe, unapproved recipe,
fetch policy denied, high-risk recipe.
Retryable errors: adapter/network failures, unexpected exceptions.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from harvester.db.models import Job
from harvester.jobs.crawl_execution import (
    CrawlExecutionError,
    execute_crawl,
)
from harvester.jobs.repository import complete_job, fail_job

logger = logging.getLogger(__name__)


def _dead_letter_job(session: Session, job: Job, error_message: str) -> None:
    """Mark a job as dead-letter without creating a retry.

    Used for permanent errors where retrying would never succeed.
    """
    job.last_error = error_message
    job.locked_by = None
    job.locked_until = None
    job.attempts += 1
    job.status = "dead"
    session.commit()


def process_crawl_job(session: Session, job: Job) -> bool:
    """Process a single crawl job.

    Returns ``True`` if the job was completed successfully, ``False`` if the
    job was failed, dead-lettered, or skipped.

    Error classification:
    - **Permanent** (dead-letter): Missing payload fields, source/recipe not
      found, recipe not approved, high-risk recipe, fetch policy denied.
    - **Retryable** (fail_job): Adapter errors, network errors, archive write
      errors.

    Parameters
    ----------
    session : Session
        Active database session.
    job : Job
        The crawl job to process (must be in ``running`` status).
    """
    payload = job.payload or {}

    # --- Validate payload (permanent errors) ---
    source_id_raw = payload.get("source_id")
    recipe_id_raw = payload.get("recipe_id")

    if not source_id_raw:
        _dead_letter_job(session, job, "Missing source_id in job payload")
        return False

    if not recipe_id_raw:
        _dead_letter_job(session, job, "Missing recipe_id in job payload")
        return False

    try:
        source_id = uuid.UUID(str(source_id_raw))
    except (ValueError, AttributeError):
        _dead_letter_job(
            session, job, f"Invalid source_id in payload: {source_id_raw!r}"
        )
        return False

    try:
        recipe_id = uuid.UUID(str(recipe_id_raw))
    except (ValueError, AttributeError):
        _dead_letter_job(
            session, job, f"Invalid recipe_id in payload: {recipe_id_raw!r}"
        )
        return False

    # Parse optional topic_watch_id
    topic_watch_id: uuid.UUID | None = None
    topic_id_raw = payload.get("topic_watch_id")
    if topic_id_raw:
        try:
            topic_watch_id = uuid.UUID(str(topic_id_raw))
        except (ValueError, AttributeError):
            _dead_letter_job(
                session,
                job,
                f"Invalid topic_watch_id in payload: {topic_id_raw!r}",
            )
            return False

    target_id: uuid.UUID | None = None
    target_id_raw = payload.get("target_id")
    if target_id_raw:
        try:
            target_id = uuid.UUID(str(target_id_raw))
        except (ValueError, AttributeError):
            _dead_letter_job(
                session,
                job,
                f"Invalid target_id in payload: {target_id_raw!r}",
            )
            return False

    # --- Execute crawl ---
    try:
        result = execute_crawl(
            session,
            source_id=source_id,
            recipe_id=recipe_id,
            actor="scheduler",
            topic_watch_id=topic_watch_id,
            target_id=target_id,
        )
    except CrawlExecutionError as exc:
        if exc.retryable:
            # Retryable error: use fail_job for retry/dead-letter flow
            logger.warning(
                "Retryable crawl error for job %s: %s", job.id, exc
            )
            fail_job(session, job.id, str(exc))
            return False
        else:
            # Permanent error: dead-letter directly
            logger.warning(
                "Permanent crawl error for job %s: %s", job.id, exc
            )
            _dead_letter_job(session, job, str(exc))
            return False

    if result.status == "completed":
        complete_job(session, job.id)
        return True
    else:
        # Crawl completed but with non-success status (e.g. policy denied)
        # This is a permanent outcome
        error_msg = result.error_message or "Crawl failed"
        _dead_letter_job(session, job, error_msg)
        return False
