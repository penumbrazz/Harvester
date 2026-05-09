"""Keyword search over content item titles.

Uses PostgreSQL ILIKE for case-insensitive substring matching against
the title column of the latest item version per content item.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import ContentItem, ItemVersion


def keyword_search(
    session: Session,
    query: str,
    *,
    source_id: uuid.UUID | None = None,
    topic_watch_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Search content items by keyword in their title.

    Returns the latest item version for each matching content item,
    filtered by the given keyword (case-insensitive ILIKE match) and
    optional source/topic constraints.

    Args:
        session: SQLAlchemy ORM session.
        query: Search term (empty string returns no results).
        source_id: Optional filter by source.
        topic_watch_id: Optional filter by topic watch.
        limit: Maximum number of results.
        offset: Pagination offset.

    Returns:
        List of dicts with keys: item_id, title, canonical_url,
        source_id, version_id, created_at.
    """
    if not query or not query.strip():
        return []

    # Subquery: latest version per content_item
    latest_version = (
        sa.select(
            ItemVersion.content_item_id,
            sa.func.max(ItemVersion.created_at).label("max_created_at"),
        )
        .group_by(ItemVersion.content_item_id)
        .subquery()
    )

    # Main query: join content_items with their latest item_version
    stmt = (
        sa.select(
            ContentItem.id.label("item_id"),
            ContentItem.title,
            ContentItem.canonical_url,
            ContentItem.source_id,
            ItemVersion.id.label("version_id"),
            ItemVersion.created_at,
        )
        .join(ItemVersion, ItemVersion.content_item_id == ContentItem.id)
        .join(
            latest_version,
            sa.and_(
                latest_version.c.content_item_id == ItemVersion.content_item_id,
                latest_version.c.max_created_at == ItemVersion.created_at,
            ),
        )
        .where(ContentItem.title.ilike(f"%{query}%"))
    )

    if source_id is not None:
        stmt = stmt.where(ContentItem.source_id == source_id)
    if topic_watch_id is not None:
        stmt = stmt.where(ContentItem.topic_watch_id == topic_watch_id)

    stmt = stmt.order_by(ItemVersion.created_at.desc()).limit(limit).offset(offset)

    rows = session.execute(stmt).fetchall()
    return [row._mapping for row in rows]
