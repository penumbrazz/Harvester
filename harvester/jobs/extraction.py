"""Extraction service — read raw payload, run extractor, feed pipeline."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, CrawlRun, CrawlTarget, RawObject, Recipe, Source
from harvester.domain.audit import write_audit
from harvester.domain.discovery_scope import (
    parse_discovery_scope,
    validate_discovered_target,
)
from harvester.extractors.base import CandidateItem, normalize_extraction_output
from harvester.extractors.registry import get_extractor
from harvester.jobs.crawl_targets import (
    create_crawl_job_for_target,
    upsert_crawl_target,
)
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)
from harvester.search.chunking import chunk_text
from harvester.search.embedding import create_embedding_jobs

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
        raise ExtractionError(f"Archive file not found: {path}", retryable=True)
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
    2. Resolve actual URL (target URL for target crawls, else source URL)
    3. Match extractor by actual URL
    4. Read raw payload from archive
    5. Run extractor to get candidate items
    6. Upsert content items, observations, and versions via pipeline
    """
    # 1. Load raw_object
    raw_object = session.get(RawObject, raw_object_id)
    if raw_object is None:
        raise ExtractionError(f"RawObject {raw_object_id} not found", retryable=False)

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

    # 2. Resolve the actual URL: use target URL for target crawls
    crawl_target = session.scalar(
        sa.select(CrawlTarget)
        .where(CrawlTarget.last_raw_object_id == raw_object_id)
        .limit(1)
    )
    actual_url = crawl_target.target_url if crawl_target else source_url

    # 3. Match extractor
    extractor = get_extractor(actual_url, content_type=raw_object.content_type)
    if extractor is None:
        logger.info(
            "extract.skip raw=%s no_extractor_for url=%s",
            raw_object_id,
            actual_url,
        )
        return ExtractionResult(
            raw_object_id=raw_object_id,
            items_extracted=0,
            versions_created=0,
            skipped=True,
            reason=f"No extractor registered for URL: {actual_url}",
        )

    # 4. Read payload
    if not raw_object.storage_uri:
        raise ExtractionError(
            f"RawObject {raw_object_id} has no storage_uri", retryable=False
        )

    logger.info(
        "extract.start raw=%s source=%s url=%s extractor=%s",
        raw_object_id,
        source.id,
        actual_url,
        type(extractor).__name__,
    )

    payload = _read_payload(raw_object.storage_uri)

    # 5. Run extractor
    metadata = {
        "source_id": str(source.id),
        "source_url": source_url,
        "content_type": raw_object.content_type,
        "target_url": crawl_target.target_url if crawl_target else None,
        "external_item_id": (crawl_target.external_item_id if crawl_target else None),
    }
    output = normalize_extraction_output(extractor.extract(metadata, payload))
    candidates: list[CandidateItem] = output.items

    logger.info(
        "extract.candidates raw=%s count=%d",
        raw_object_id,
        len(candidates),
    )

    # 6. Upsert through pipeline
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

        content_hash = (
            "sha256:"
            + hashlib.sha256(candidate.content_text.encode("utf-8")).hexdigest()
        )

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
            _create_chunks_and_embedding_jobs(session, version)

    _process_discovered_targets(
        session,
        raw_object=raw_object,
        source=source,
        discovered_targets=output.discovered_targets,
        actor=actor,
    )

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
        raw_object_id,
        items_count,
        versions_count,
    )

    return ExtractionResult(
        raw_object_id=raw_object_id,
        items_extracted=items_count,
        versions_created=versions_count,
    )


def _process_discovered_targets(
    session: Session,
    *,
    raw_object: RawObject,
    source: Source,
    discovered_targets: list,
    actor: str,
) -> None:
    """Persist in-scope discovered targets and enqueue crawl jobs."""
    if not discovered_targets:
        return

    recipe = _find_recipe_for_raw_object(session, raw_object.id)
    if recipe is None:
        logger.info(
            "discovery.skip raw=%s no_recipe_found",
            raw_object.id,
        )
        return
    scope = parse_discovery_scope(recipe.config)

    targets_seen = 0
    for discovered in discovered_targets:
        content_type = discovered.content_type or _content_type_for_media_type(
            discovered.media_type
        )
        decision = validate_discovered_target(
            scope,
            target_url=discovered.target_url,
            content_type=content_type,
            depth=discovered.depth,
            targets_seen=targets_seen,
        )
        if not decision.allowed:
            write_audit(
                session,
                actor=actor,
                action="crawl_target_skipped",
                entity_type="raw_object",
                entity_id=raw_object.id,
                after_state={
                    "target_url": discovered.target_url,
                    "target_role": discovered.target_role,
                },
                reason=decision.reason,
            )
            continue

        target, _ = upsert_crawl_target(
            session,
            source_id=source.id,
            recipe_id=recipe.id,
            target_url=discovered.target_url,
            target_role=discovered.target_role,
            media_type=discovered.media_type,
            parent_target_id=_parse_optional_uuid(discovered.parent_target_id),
            discovered_from_raw_object_id=raw_object.id,
            external_item_id=discovered.external_item_id,
            depth=discovered.depth,
            priority=discovered.priority,
        )
        create_crawl_job_for_target(session, target, auto_commit=False)
        targets_seen += 1


def _find_recipe_for_raw_object(
    session: Session, raw_object_id: uuid.UUID
) -> Recipe | None:
    """Return the most recent recipe associated with a raw object's crawl run."""
    return session.scalar(
        sa.select(Recipe)
        .join(CrawlRun, CrawlRun.recipe_id == Recipe.id)
        .where(CrawlRun.raw_object_id == raw_object_id)
        .order_by(CrawlRun.created_at.desc())
        .limit(1)
    )


def _content_type_for_media_type(media_type: str) -> str:
    """Infer a validation content type from a target media type."""
    if media_type == "pdf":
        return "application/pdf"
    if media_type == "html":
        return "text/html"
    return "application/octet-stream"


def _create_chunks_and_embedding_jobs(
    session: Session,
    version: ItemVersion,
) -> None:
    """Chunk item version text and enqueue embedding jobs."""
    if not version.normalized_text:
        return

    chunks_data = chunk_text(version.normalized_text)
    if not chunks_data:
        return

    for chunk_data in chunks_data:
        chunk = Chunk(
            id=uuid.uuid4(),
            item_version_id=version.id,
            chunk_index=chunk_data["chunk_index"],
            text=chunk_data["text"],
            token_count=chunk_data["token_count"],
            embedding_status="pending",
            created_at=datetime.now(UTC),
        )
        session.add(chunk)

    session.flush()
    create_embedding_jobs(session, version.id)


def _parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    """Parse an optional UUID string."""
    if value is None:
        return None
    return uuid.UUID(str(value))
