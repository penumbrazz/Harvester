"""Embedding job creation for the search pipeline.

Embedding jobs are created ONLY for chunks derived from
``item_versions.normalized_text``.  Raw HTML/API payloads are never embedded
directly.
"""

from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, Job
from harvester.jobs.repository import create_job

logger = logging.getLogger(__name__)


def create_embedding_jobs(
    session: Session,
    item_version_id: uuid.UUID,
) -> list[Job]:
    """Create ``embed_chunks`` jobs for all pending chunks of an item version.

    Only chunks with ``embedding_status='pending'`` are considered.  Chunks
    that are already embedded (``done``) or in an error state (``failed``) are
    skipped.

    Parameters
    ----------
    session : Session
        Active database session.
    item_version_id : uuid.UUID
        The item version whose chunks need embedding.

    Returns
    -------
    list[Job]
        The newly created ``embed_chunks`` jobs.
    """
    pending_chunks = session.scalars(
        sa.select(Chunk).where(
            Chunk.item_version_id == item_version_id,
            Chunk.embedding_status == "pending",
        ).order_by(Chunk.chunk_index)
    ).all()

    created: list[Job] = []
    for chunk in pending_chunks:
        job = create_job(
            session,
            job_type="embed_chunks",
            payload={
                "item_version_id": str(item_version_id),
                "chunk_id": str(chunk.id),
            },
            idempotency_key=f"embed-{chunk.id}",
        )
        if job is not None:
            created.append(job)
            logger.info(
                "Created embed_chunks job %s for chunk %s (item_version %s)",
                job.id,
                chunk.id,
                item_version_id,
            )

    return created
