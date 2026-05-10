"""Vector (embedding) search over chunks.

Uses pgvector cosine distance (<=>) to find the nearest-neighbor
chunks for a given query embedding.  Results are collapsed by dedup
group so each group appears at most once.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, ContentItem, ItemVersion
from harvester.search.dedup import collapse_dedup_groups


def vector_search(
    session: Session,
    query_embedding: list[float],
    *,
    limit: int = 20,
    source_id: uuid.UUID | None = None,
    topic_watch_id: uuid.UUID | None = None,
) -> list[dict]:
    """Search chunks by cosine distance to the given embedding.

    Only considers chunks where ``embedding IS NOT NULL`` and
    ``embedding_status = 'ready'``.  Results are ordered by ascending
    cosine distance.  Dedup groups are collapsed so that only the
    canonical version is returned per group.

    Args:
        session: SQLAlchemy ORM session.
        query_embedding: The query vector (1536 dimensions).
        limit: Maximum number of results.
        source_id: Optional filter by source.
        topic_watch_id: Optional filter by topic watch.

    Returns:
        List of dicts with keys: chunk_id, item_version_id, text,
        distance, content_item_id, title.
    """
    # Fetch more rows than requested to compensate for dedup collapse.
    fetch_limit = limit * 3

    # Build the distance expression using pgvector's cosine operator
    distance_col = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        sa.select(
            Chunk.id.label("chunk_id"),
            Chunk.item_version_id,
            Chunk.text,
            distance_col,
            ContentItem.id.label("content_item_id"),
            ContentItem.title,
        )
        .join(ItemVersion, ItemVersion.id == Chunk.item_version_id)
        .join(ContentItem, ContentItem.id == ItemVersion.content_item_id)
        .where(Chunk.embedding.is_not(None))
        .where(Chunk.embedding_status == "ready")
    )

    if source_id is not None:
        stmt = stmt.where(ContentItem.source_id == source_id)
    if topic_watch_id is not None:
        stmt = stmt.where(ContentItem.topic_watch_id == topic_watch_id)

    stmt = stmt.order_by("distance").limit(fetch_limit)

    rows = session.execute(stmt).fetchall()

    # Collapse dedup groups at the version level.
    version_ids = list({row.item_version_id for row in rows})
    canonical_ids = set(collapse_dedup_groups(session, version_ids))

    # Filter rows to keep only canonical versions, preserving order.
    results = [row._mapping for row in rows if row.item_version_id in canonical_ids]
    return results[:limit]
