"""Vector (embedding) search over chunks.

Uses pgvector cosine distance (<=>) to find the nearest-neighbor
chunks for a given query embedding.
"""

import uuid

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, ContentItem, ItemVersion


def vector_search(
    session: Session,
    query_embedding: list[float],
    *,
    limit: int = 20,
) -> list[dict]:
    """Search chunks by cosine distance to the given embedding.

    Only considers chunks where ``embedding IS NOT NULL`` and
    ``embedding_status = 'ready'``.  Results are ordered by ascending
    cosine distance.

    Args:
        session: SQLAlchemy ORM session.
        query_embedding: The query vector (1536 dimensions).
        limit: Maximum number of results.

    Returns:
        List of dicts with keys: chunk_id, item_version_id, text,
        distance, content_item_id, title.
    """
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
        .order_by("distance")
        .limit(limit)
    )

    rows = session.execute(stmt).fetchall()
    return [row._mapping for row in rows]
