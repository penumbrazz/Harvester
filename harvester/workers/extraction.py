"""Extraction job handler — processes a single extract job."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from harvester.db.models import Job
from harvester.jobs.extraction import ExtractionError, execute_extraction
from harvester.jobs.repository import complete_job, fail_job

logger = logging.getLogger(__name__)


def _dead_letter_job(session: Session, job: Job, error_message: str) -> None:
    """Mark a job as dead-letter without creating a retry."""
    job.last_error = error_message
    job.locked_by = None
    job.locked_until = None
    job.attempts += 1
    job.status = "dead"
    session.commit()


def process_extract_job(session: Session, job: Job) -> bool:
    """Process a single extraction job.

    Returns True if the job was completed successfully.
    """
    payload = job.payload or {}

    raw_object_id_raw = payload.get("raw_object_id")
    if not raw_object_id_raw:
        _dead_letter_job(session, job, "Missing raw_object_id in job payload")
        return False

    try:
        raw_object_id = uuid.UUID(str(raw_object_id_raw))
    except (ValueError, AttributeError):
        _dead_letter_job(
            session, job, f"Invalid raw_object_id: {raw_object_id_raw!r}"
        )
        return False

    try:
        result = execute_extraction(
            session,
            raw_object_id=raw_object_id,
            actor="worker",
        )
    except ExtractionError as exc:
        if exc.retryable:
            logger.warning(
                "Retryable extraction error for job %s: %s", job.id, exc
            )
            fail_job(session, job.id, str(exc))
            return False
        else:
            logger.warning(
                "Permanent extraction error for job %s: %s", job.id, exc
            )
            _dead_letter_job(session, job, str(exc))
            return False

    if result.skipped:
        logger.info(
            "Extraction skipped for job %s: %s", job.id, result.reason
        )

    complete_job(session, job.id)
    return True
