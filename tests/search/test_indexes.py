"""Verify that search-related database indexes exist in the migrated schema.

These tests use the ``db_connection`` fixture (raw SQLAlchemy Connection)
and query the ``pg_class`` / ``pg_indexes`` system catalogs so that we
confirm the Alembic migration actually created the expected indexes.
"""

import pytest
import sqlalchemy as sa


def _index_exists(conn, index_name: str) -> bool:
    """Return True if the given index exists in the current database."""
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM pg_class WHERE relname = :name AND relkind = 'i'"
        ),
        {"name": index_name},
    )
    return result.scalar() == 1


def _get_index_columns(conn, index_name: str) -> list[str]:
    """Return the column names for the given index (empty list if not found)."""
    result = conn.execute(
        sa.text(
            "SELECT a.attname "
            "FROM pg_class c "
            "JOIN pg_index i ON i.indexrelid = c.oid "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid "
            "    AND a.attnum = ANY(i.indkey) "
            "WHERE c.relname = :name "
            "ORDER BY array_position(i.indkey, a.attnum)"
        ),
        {"name": index_name},
    )
    return [row[0] for row in result]


class TestSearchIndexes:
    """Validate that the search migration created the required indexes."""

    def test_item_versions_item_created_index_exists(self, db_connection):
        """The composite index on (content_item_id, created_at DESC) must exist."""
        assert _index_exists(db_connection, "ix_item_versions_item_created")

    def test_item_versions_item_created_index_columns(self, db_connection):
        """The index must cover content_item_id and created_at."""
        cols = _get_index_columns(db_connection, "ix_item_versions_item_created")
        assert "content_item_id" in cols
        assert "created_at" in cols

    def test_content_items_source_id_index_exists(self, db_connection):
        """The index on content_items(source_id) must exist."""
        assert _index_exists(db_connection, "ix_content_items_source_id")

    def test_content_items_topic_watch_id_index_exists(self, db_connection):
        """The index on content_items(topic_watch_id) must exist."""
        assert _index_exists(db_connection, "ix_content_items_topic_watch_id")

    def test_chunks_embedding_status_index_exists(self, db_connection):
        """The index on chunks(embedding_status) must exist."""
        assert _index_exists(db_connection, "ix_chunks_embedding_status")

    def test_content_items_title_trgm_index_exists(self, db_connection):
        """A GIN trgm index on content_items.title must exist for keyword search."""
        result = db_connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE tablename = 'content_items' "
                "AND indexdef LIKE '%gin_trgm_ops%'"
            )
        )
        assert result.scalar() >= 1, (
            "Expected at least one pg_trgm GIN index on content_items.title"
        )
