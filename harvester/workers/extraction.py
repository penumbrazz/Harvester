"""Extraction job handler — processes a single extract job."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from harvester.db.models import Job
from harvester.jobs.extraction import ExtractionError, execute_extraction
from harvester.jobs.repository import complete_job, dead_letter_job, fail_job

logger = logging.getLogger(__name__)


def process_extract_job(session: Session, job: Job) -> bool:
    """Process a single extraction job.

    Returns True if the job was completed successfully.
    """
    payload = job.payload or {}

    raw_object_id_raw = payload.get("raw_object_id")
    if not raw_object_id_raw:
        dead_letter_job(session, job.id, "Missing raw_object_id in job payload")
        return False

    try:
        raw_object_id = uuid.UUID(str(raw_object_id_raw))
    except (ValueError, AttributeError):
        dead_letter_job(
            session, job.id, f"Invalid raw_object_id: {raw_object_id_raw!r}"
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
            logger.warning("Retryable extraction error for job %s: %s", job.id, exc)
            fail_job(session, job.id, str(exc))
            return False
        else:
            logger.warning("Permanent extraction error for job %s: %s", job.id, exc)
            dead_letter_job(session, job.id, str(exc))
            return False

    if result.skipped:
        logger.info("Extraction skipped for job %s: %s", job.id, result.reason)

    complete_job(session, job.id)
    return True
