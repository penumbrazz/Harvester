"""add search indexes

Revision ID: a96be82a295e
Revises: 484b2c3f36a4
Create Date: 2026-05-09 19:22:26.679406
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a96be82a295e'
down_revision: Union[str, None] = '484b2c3f36a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for trigram-based text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Composite index for latest-version lookups
    op.execute(
        "CREATE INDEX ix_item_versions_item_created "
        "ON item_versions (content_item_id, created_at DESC)"
    )

    # Foreign-key lookup indexes on content_items
    op.create_index(
        "ix_content_items_source_id", "content_items", ["source_id"],
    )
    op.create_index(
        "ix_content_items_topic_watch_id", "content_items", ["topic_watch_id"],
    )

    # Embedding status filter index on chunks
    op.create_index(
        "ix_chunks_embedding_status", "chunks", ["embedding_status"],
    )

    # GIN trigram index on content_items.title for keyword search
    op.execute(
        "CREATE INDEX ix_content_items_title_trgm "
        "ON content_items USING gin (title gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_content_items_title_trgm")
    op.drop_index("ix_chunks_embedding_status", table_name="chunks")
    op.drop_index("ix_content_items_topic_watch_id", table_name="content_items")
    op.drop_index("ix_content_items_source_id", table_name="content_items")
    op.execute("DROP INDEX IF EXISTS ix_item_versions_item_created")
