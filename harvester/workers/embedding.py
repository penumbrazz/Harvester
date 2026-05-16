"""Embed chunks job handler — processes a single embed_chunks job."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from harvester.db.models import Chunk, Job
from harvester.jobs.repository import complete_job, fail_job

logger = logging.getLogger(__name__)

_EMBEDDING_DIMENSION = 1536


def _dead_letter_job(session: Session, job: Job, error_message: str) -> None:
    """Mark a job as dead-letter without creating a retry.

    Used for permanent errors (invalid payload, missing chunk) where retrying
    would never succeed.
    """
    job.last_error = error_message
    job.locked_by = None
    job.locked_until = None
    job.attempts += 1
    job.status = "dead"
    session.commit()


def process_embed_chunks_job(
    session: Session,
    job: Job,
    adapter,
    model_name: str,
) -> bool:
    """Process a single ``embed_chunks`` job.

    Returns ``True`` if the job was completed successfully, ``False`` if the
    job was failed or skipped.

    - If the chunk is already ``ready``, the job is completed without re-embedding.
    - If the adapter raises, ``fail_job`` is called.  If the job transitions to
      ``dead`` status (all retries exhausted), the chunk is marked ``failed``.
    - If the payload is invalid or the chunk does not exist, the job is
      dead-lettered directly — retrying would never succeed.

    Parameters
    ----------
    session : Session
        Active database session.
    job : Job
        The ``embed_chunks`` job to process (must be in ``running`` status).
    adapter
        An object with an ``embed(text: str) -> list[float]`` method.
    model_name : str
        The model identifier to write into ``chunks.embedding_model``.
    """
    payload = job.payload or {}
    chunk_id_raw = payload.get("chunk_id")

    # --- Validate payload (permanent errors — dead-letter directly) ---
    if not chunk_id_raw:
        _dead_letter_job(session, job, "Missing chunk_id in job payload")
        return False

    try:
        chunk_id = uuid.UUID(str(chunk_id_raw))
    except (ValueError, AttributeError):
        _dead_letter_job(session, job, f"Invalid chunk_id in payload: {chunk_id_raw!r}")
        return False

    # --- Load chunk (permanent error — dead-letter directly) ---
    chunk = session.get(Chunk, chunk_id)
    if chunk is None:
        _dead_letter_job(session, job, f"Chunk not found: {chunk_id}")
        return False

    # --- Skip if already ready ---
    if chunk.embedding_status == "ready":
        complete_job(session, job.id)
        return True

    # --- Generate embedding ---
    try:
        embedding = adapter.embed(chunk.text)
    except Exception as exc:
        logger.warning(
            "Adapter failed for chunk %s (job %s): %s", chunk_id, job.id, exc
        )
        fail_job(session, job.id, f"Adapter error: {exc}")

        # After fail_job, re-read status to check if retry budget exhausted.
        # retry jobs inherit cumulative attempts, so dead-letter is reachable.
        session.expire(job, ["status"])
        if job.status == "dead":
            chunk.embedding_status = "failed"
            session.commit()

        return False

    # --- Validate embedding dimension ---
    if len(embedding) != _EMBEDDING_DIMENSION:
        logger.error(
            "Embedding dimension mismatch for chunk %s: expected %d, got %d",
            chunk_id,
            _EMBEDDING_DIMENSION,
            len(embedding),
        )
        fail_job(
            session,
            job.id,
            f"Embedding dimension mismatch: expected {_EMBEDDING_DIMENSION}, got {len(embedding)}",
        )

        session.expire(job, ["status"])
        if job.status == "dead":
            chunk.embedding_status = "failed"
            session.commit()

        return False

    # --- Write back ---
    chunk.embedding = embedding
    chunk.embedding_model = model_name
    chunk.embedding_status = "ready"
    complete_job(session, job.id)
    return True
