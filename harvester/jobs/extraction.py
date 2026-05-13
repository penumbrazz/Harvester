"""Extraction service — read raw payload, run extractor, feed pipeline."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from harvester.db.models import RawObject, Source
from harvester.domain.audit import write_audit
from harvester.extractors.base import CandidateItem
from harvester.extractors.registry import get_extractor_for_url
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when extraction fails."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class ExtractionResult:
    """Result of an extraction run."""

    raw_object_id: uuid.UUID
    items_extracted: int
    versions_created: int
    skipped: bool = False
    reason: str | None = None


def _read_payload(storage_uri: str) -> bytes:
    """Read raw payload from local archive storage URI.

    Expected format: file:///absolute/path/to/file.raw
    """
    if not storage_uri.startswith("file://"):
        raise ExtractionError(
            f"Unsupported storage URI scheme: {storage_uri}", retryable=False
        )
    path = Path(storage_uri[7:])
    if not path.exists():
        raise ExtractionError(
            f"Archive file not found: {path}", retryable=True
        )
    return path.read_bytes()


def execute_extraction(
    session: Session,
    *,
    raw_object_id: uuid.UUID,
    actor: str = "system",
) -> ExtractionResult:
    """Extract content items from a raw object.

    Steps:
    1. Load raw_object metadata and source
    2. Match extractor by source URL
    3. Read raw payload from archive
    4. Run extractor to get candidate items
    5. Upsert content items, observations, and versions via pipeline
    """
    # 1. Load raw_object
    raw_object = session.get(RawObject, raw_object_id)
    if raw_object is None:
        raise ExtractionError(
            f"RawObject {raw_object_id} not found", retryable=False
        )

    if not raw_object.source_id:
        raise ExtractionError(
            f"RawObject {raw_object_id} has no source_id", retryable=False
        )

    source = session.get(Source, raw_object.source_id)
    if source is None:
        raise ExtractionError(
            f"Source {raw_object.source_id} not found", retryable=False
        )

    source_url = source.url or ""

    # 2. Match extractor
    extractor = get_extractor_for_url(source_url)
    if extractor is None:
        logger.info(
            "extract.skip raw=%s no_extractor_for url=%s",
            raw_object_id, source_url,
        )
        return ExtractionResult(
            raw_object_id=raw_object_id,
            items_extracted=0,
            versions_created=0,
            skipped=True,
            reason=f"No extractor registered for URL: {source_url}",
        )

    # 3. Read payload
    if not raw_object.storage_uri:
        raise ExtractionError(
            f"RawObject {raw_object_id} has no storage_uri", retryable=False
        )

    logger.info(
        "extract.start raw=%s source=%s url=%s extractor=%s",
        raw_object_id, source.id, source_url,
        type(extractor).__name__,
    )

    payload = _read_payload(raw_object.storage_uri)

    # 4. Run extractor
    metadata = {
        "source_id": str(source.id),
        "source_url": source_url,
        "content_type": raw_object.content_type,
    }
    candidates: list[CandidateItem] = extractor.extract(metadata, payload)

    logger.info(
        "extract.candidates raw=%s count=%d", raw_object_id, len(candidates),
    )

    # 5. Upsert through pipeline
    items_count = 0
    versions_count = 0

    for candidate in candidates:
        content_item, _ = upsert_content_item(
            session,
            source_id=source.id,
            external_item_id=candidate.external_item_id,
            item_type=candidate.item_type,
            original_url=candidate.original_url,
            final_url=candidate.final_url,
            canonical_url=candidate.canonical_url,
            canonical_url_hash=candidate.canonical_url_hash,
            title=candidate.title,
        )
        items_count += 1

        create_observation(
            session,
            content_item_id=content_item.id,
            raw_object_id=raw_object_id,
            position=candidate.position,
            observed_url=candidate.observed_url,
            payload_hash=candidate.payload_hash,
            snippet=candidate.snippet,
        )

        content_hash = "sha256:" + hashlib.sha256(
            candidate.content_text.encode("utf-8")
        ).hexdigest()

        version, created = create_version_if_changed(
            session,
            content_item_id=content_item.id,
            content_hash=content_hash,
            normalized_text=candidate.content_text,
            language=candidate.language,
            raw_object_id=raw_object_id,
        )
        if created:
            versions_count += 1

    session.flush()

    write_audit(
        session,
        actor=actor,
        action="extraction_completed",
        entity_type="raw_object",
        entity_id=raw_object_id,
        after_state={
            "items_extracted": items_count,
            "versions_created": versions_count,
            "extractor": type(extractor).__name__,
        },
    )

    logger.info(
        "extract.completed raw=%s items=%d versions=%d",
        raw_object_id, items_count, versions_count,
    )

    return ExtractionResult(
        raw_object_id=raw_object_id,
        items_extracted=items_count,
        versions_created=versions_count,
    )
