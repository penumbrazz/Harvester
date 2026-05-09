"""Extraction and dedup pipeline — content item upsert, observation, versioning, and downstream jobs."""

from __future__ import annotations

import datetime
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import ContentItem, ItemObservation, ItemVersion, Job
from harvester.jobs.repository import create_job

logger = logging.getLogger(__name__)


def upsert_content_item(
    session: Session,
    *,
    source_id: uuid.UUID,
    external_item_id: str | None = None,
    item_type: str,
    original_url: str | None = None,
    final_url: str | None = None,
    canonical_url: str | None = None,
    canonical_url_hash: str | None = None,
    title: str | None = None,
) -> tuple[ContentItem, bool]:
    """Create or update a content item identified by (source_id, external_item_id).

    Parameters
    ----------
    session : Session
        Active database session.
    source_id : uuid.UUID
        The source this item was extracted from.
    external_item_id : str or None
        External identifier for dedup (e.g. RSS GUID).  When ``None`` a new
        item is always created.
    item_type : str
        Type of the content item (e.g. ``"article"``, ``"post"``).
    original_url, final_url, canonical_url : str or None
        Various URL representations of the item.
    canonical_url_hash : str or None
        SHA-256 hash of the canonical URL for index lookups.
    title : str or None
        Item title.

    Returns
    -------
    tuple[ContentItem, bool]
        The content item instance and a flag indicating whether it was newly
        created (``True``) or updated (``False``).
    """
    existing: ContentItem | None = None

    if external_item_id is not None:
        existing = session.scalar(
            sa.select(ContentItem).where(
                ContentItem.source_id == source_id,
                ContentItem.external_item_id == external_item_id,
            )
        )
    elif canonical_url_hash is not None:
        # Weak key fallback: upsert by canonical URL hash within the same source.
        existing = session.scalar(
            sa.select(ContentItem).where(
                ContentItem.source_id == source_id,
                ContentItem.canonical_url_hash == canonical_url_hash,
            )
        )

    now = datetime.datetime.now(datetime.UTC)

    if existing is not None:
        # Update mutable fields on the existing item.
        if title is not None:
            existing.title = title
        if original_url is not None:
            existing.original_url = original_url
        if final_url is not None:
            existing.final_url = final_url
        if canonical_url is not None:
            existing.canonical_url = canonical_url
        if canonical_url_hash is not None:
            existing.canonical_url_hash = canonical_url_hash
        existing.updated_at = now
        session.flush()
        return existing, False

    item = ContentItem(
        id=uuid.uuid4(),
        item_type=item_type,
        external_item_id=external_item_id,
        source_id=source_id,
        original_url=original_url,
        final_url=final_url,
        canonical_url=canonical_url,
        canonical_url_hash=canonical_url_hash,
        title=title,
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    session.flush()
    return item, True


def create_observation(
    session: Session,
    *,
    content_item_id: uuid.UUID,
    raw_object_id: uuid.UUID,
    extraction_run_id: uuid.UUID | None = None,
    position: int | None = None,
    observed_url: str | None = None,
    payload_hash: str | None = None,
    snippet: str | None = None,
) -> ItemObservation:
    """Record an observation linking a content item to a raw object.

    If an observation for (content_item_id, raw_object_id) already exists,
    updates ``last_seen`` and mutable fields instead of inserting a duplicate.

    Parameters
    ----------
    session : Session
        Active database session.
    content_item_id : uuid.UUID
        The content item that was observed.
    raw_object_id : uuid.UUID
        The raw object from which the item was extracted.
    extraction_run_id : uuid.UUID or None
        Optional extraction run identifier.
    position : int or None
        Position of the item within the raw payload (e.g. index in a feed).
    observed_url : str or None
        URL at which the item was observed.
    payload_hash : str or None
        Hash of the relevant payload slice.
    snippet : str or None
        Short text snippet of the observed content.

    Returns
    -------
    ItemObservation
        The persisted observation record.
    """
    existing = session.scalar(
        sa.select(ItemObservation).where(
            ItemObservation.content_item_id == content_item_id,
            ItemObservation.raw_object_id == raw_object_id,
        )
    )

    now = datetime.datetime.now(datetime.UTC)

    if existing is not None:
        existing.last_seen = now
        if snippet is not None:
            existing.snippet = snippet
        if position is not None:
            existing.position = position
        session.flush()
        return existing

    obs = ItemObservation(
        id=uuid.uuid4(),
        content_item_id=content_item_id,
        raw_object_id=raw_object_id,
        extraction_run_id=extraction_run_id,
        position=position,
        observed_url=observed_url,
        payload_hash=payload_hash,
        snippet=snippet,
        created_at=now,
        last_seen=now,
    )
    session.add(obs)
    session.flush()
    return obs


def create_version_if_changed(
    session: Session,
    *,
    content_item_id: uuid.UUID,
    content_hash: str,
    simhash: str | None = None,
    normalized_text: str | None = None,
    language: str | None = None,
    raw_object_id: uuid.UUID | None = None,
    dedup_group_id: uuid.UUID | None = None,
) -> tuple[ItemVersion, bool]:
    """Create a new item version only if the content has changed.

    Dedup is keyed on ``(content_item_id, content_hash)``.  If a version with
    the same hash already exists, no new row is inserted.

    Parameters
    ----------
    session : Session
        Active database session.
    content_item_id : uuid.UUID
        The parent content item.
    content_hash : str
        Hash of the item content (SHA-256 or similar).
    simhash : str or None
        Similarity hash for near-duplicate detection.
    normalized_text : str or None
        Normalized full text of the item version.
    language : str or None
        ISO-639 language code.
    raw_object_id : uuid.UUID or None
        The raw object this version was extracted from.
    dedup_group_id : uuid.UUID or None
        Optional dedup group for near-duplicate clustering.

    Returns
    -------
    tuple[ItemVersion, bool]
        The item version and a flag indicating whether it was newly created.
    """
    existing = session.scalar(
        sa.select(ItemVersion).where(
            ItemVersion.content_item_id == content_item_id,
            ItemVersion.content_hash == content_hash,
        )
    )

    if existing is not None:
        return existing, False

    version = ItemVersion(
        id=uuid.uuid4(),
        content_item_id=content_item_id,
        content_hash=content_hash,
        simhash=simhash,
        normalized_text=normalized_text,
        language=language,
        raw_object_id=raw_object_id,
        dedup_group_id=dedup_group_id,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    session.add(version)
    session.flush()
    return version, True


def create_downstream_jobs(
    session: Session,
    item_version_id: uuid.UUID,
    job_types: list[str] | None = None,
) -> list[Job]:
    """Create downstream processing jobs for a newly created item version.

    Parameters
    ----------
    session : Session
        Active database session.
    item_version_id : uuid.UUID
        The item version that triggered the downstream jobs.
    job_types : list[str] or None
        Job types to create.  Defaults to ``["embed_chunks"]``.

    Returns
    -------
    list[Job]
        The created job instances.
    """
    if job_types is None:
        job_types = ["embed_chunks"]

    created: list[Job] = []
    for jtype in job_types:
        job = create_job(
            session,
            job_type=jtype,
            payload={"item_version_id": str(item_version_id)},
            auto_commit=False,
        )
        if job is not None:
            created.append(job)
            logger.info(
                "Created downstream job %s of type %s for item version %s",
                job.id,
                jtype,
                item_version_id,
            )

    return created
