"""Repository helpers for discovered crawl targets."""

from __future__ import annotations

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import CrawlTarget, Job
from harvester.domain.urls import compute_canonical_url_hash, normalize_url
from harvester.jobs.repository import create_job


def upsert_crawl_target(
    session: Session,
    *,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    target_url: str,
    target_role: str,
    media_type: str = "unknown",
    parent_target_id: uuid.UUID | None = None,
    discovered_from_raw_object_id: uuid.UUID | None = None,
    external_item_id: str | None = None,
    depth: int = 0,
    priority: int = 0,
    now: datetime.datetime | None = None,
) -> tuple[CrawlTarget, bool]:
    """Create or update a crawl target by source, role and canonical URL.

    Returns the target and whether it was newly created.
    """
    observed_at = now or datetime.datetime.now(datetime.UTC)
    canonical_url = normalize_url(target_url)
    canonical_url_hash = compute_canonical_url_hash(target_url)

    existing = session.scalar(
        sa.select(CrawlTarget).where(
            CrawlTarget.source_id == source_id,
            CrawlTarget.target_role == target_role,
            CrawlTarget.canonical_url_hash == canonical_url_hash,
        )
    )
    if existing is not None:
        existing.recipe_id = recipe_id
        existing.canonical_url = canonical_url
        existing.media_type = media_type
        existing.depth = depth
        existing.priority = priority
        existing.last_seen_at = observed_at
        existing.updated_at = observed_at
        # Only update target_url if not yet completed — avoids
        # resetting the URL after a successful crawl.
        if existing.status not in ("completed",):
            existing.target_url = target_url
        if parent_target_id is not None:
            existing.parent_target_id = parent_target_id
        if discovered_from_raw_object_id is not None:
            existing.discovered_from_raw_object_id = discovered_from_raw_object_id
        if external_item_id is not None:
            existing.external_item_id = external_item_id
        session.flush()
        return existing, False

    target = CrawlTarget(
        id=uuid.uuid4(),
        source_id=source_id,
        recipe_id=recipe_id,
        parent_target_id=parent_target_id,
        discovered_from_raw_object_id=discovered_from_raw_object_id,
        target_url=target_url,
        canonical_url=canonical_url,
        canonical_url_hash=canonical_url_hash,
        target_role=target_role,
        media_type=media_type,
        external_item_id=external_item_id,
        status="pending",
        depth=depth,
        priority=priority,
        failure_count=0,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
        created_at=observed_at,
        updated_at=observed_at,
    )
    session.add(target)
    session.flush()
    return target, True


def find_crawl_target(
    session: Session,
    *,
    source_id: uuid.UUID,
    target_role: str,
    target_url: str,
) -> CrawlTarget | None:
    """Find a crawl target by source, role and canonical target URL."""
    canonical_url_hash = compute_canonical_url_hash(target_url)
    return session.scalar(
        sa.select(CrawlTarget).where(
            CrawlTarget.source_id == source_id,
            CrawlTarget.target_role == target_role,
            CrawlTarget.canonical_url_hash == canonical_url_hash,
        )
    )


def list_crawl_targets(
    session: Session,
    *,
    source_id: uuid.UUID,
    target_role: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[CrawlTarget]:
    """List crawl targets for a source with optional role and status filters."""
    stmt = (
        sa.select(CrawlTarget)
        .where(CrawlTarget.source_id == source_id)
        .order_by(CrawlTarget.priority.desc(), CrawlTarget.last_seen_at.desc())
        .limit(limit)
    )
    if target_role is not None:
        stmt = stmt.where(CrawlTarget.target_role == target_role)
    if status is not None:
        stmt = stmt.where(CrawlTarget.status == status)
    return list(session.scalars(stmt))


def create_crawl_job_for_target(
    session: Session,
    target: CrawlTarget,
    *,
    auto_commit: bool = False,
) -> Job | None:
    """Create an idempotent crawl job for a discovered target."""
    idempotency_key = f"crawl-target:{target.id}:{target.canonical_url_hash}"
    return create_job(
        session,
        job_type="crawl",
        payload={
            "source_id": str(target.source_id),
            "recipe_id": str(target.recipe_id),
            "target_id": str(target.id),
        },
        idempotency_key=idempotency_key,
        priority=target.priority,
        source_id=str(target.source_id),
        auto_commit=auto_commit,
    )
