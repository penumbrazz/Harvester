"""Tests for content and dedup schema: content_items, item_observations, item_versions, dedup_groups, chunks."""

import sqlalchemy as sa


def _table_names(conn) -> set[str]:
    result = conn.execute(
        sa.text(
            "SELECT relname FROM pg_class "
            "WHERE relkind='r' AND relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public')"
        )
    )
    return {row[0] for row in result}


def _column_names(conn, table_name: str) -> set[str]:
    result = conn.execute(
        sa.text(
            "SELECT attname FROM pg_attribute "
            "WHERE attrelid = "
            "(SELECT oid FROM pg_class WHERE relname = :name "
            " AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')) "
            "AND attnum > 0 AND NOT attisdropped"
        ),
        {"name": table_name},
    )
    return {row[0] for row in result}


def _unique_constraints(conn, table_name: str) -> list[tuple[str, ...]]:
    """Return list of column tuples for each unique constraint."""
    result = conn.execute(
        sa.text(
            "SELECT kcu.constraint_name, kcu.column_name, kcu.ordinal_position "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name = kcu.constraint_name "
            "  AND tc.table_schema = kcu.table_schema "
            "WHERE tc.constraint_type = 'UNIQUE' "
            "  AND tc.table_name = :table AND tc.table_schema = 'public' "
            "ORDER BY kcu.constraint_name, kcu.ordinal_position"
        ),
        {"table": table_name},
    )
    constraints: dict[str, list[str]] = {}
    for row in result:
        constraints.setdefault(row[0], []).append(row[1])
    return [tuple(cols) for cols in constraints.values()]


class TestContentItemsTable:
    """Tests for the content_items table."""

    def test_table_exists(self, db_connection):
        assert "content_items" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "content_items")
        required = {
            "id", "item_type", "status", "created_at", "updated_at",
        }
        assert required.issubset(cols)

    def test_url_fields(self, db_connection):
        cols = _column_names(db_connection, "content_items")
        for col in ("original_url", "final_url", "canonical_url", "canonical_url_hash"):
            assert col in cols

    def test_external_id_column(self, db_connection):
        cols = _column_names(db_connection, "content_items")
        assert "external_item_id" in cols

    def test_source_topic_links(self, db_connection):
        cols = _column_names(db_connection, "content_items")
        assert "source_id" in cols
        assert "topic_watch_id" in cols

    def test_source_external_id_unique_constraint(self, db_connection):
        uqs = _unique_constraints(db_connection, "content_items")
        col_sets = [set(uq) for uq in uqs]
        assert {"source_id", "external_item_id"} in col_sets


class TestItemObservationsTable:
    """Tests for the item_observations table."""

    def test_table_exists(self, db_connection):
        assert "item_observations" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "item_observations")
        required = {
            "id", "content_item_id", "raw_object_id", "created_at",
        }
        assert required.issubset(cols)

    def test_extraction_and_position_columns(self, db_connection):
        cols = _column_names(db_connection, "item_observations")
        assert "extraction_run_id" in cols
        assert "position" in cols

    def test_url_and_hash_columns(self, db_connection):
        cols = _column_names(db_connection, "item_observations")
        assert "observed_url" in cols
        assert "payload_hash" in cols
        assert "snippet" in cols


class TestItemVersionsTable:
    """Tests for the item_versions table."""

    def test_table_exists(self, db_connection):
        assert "item_versions" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "item_versions")
        required = {
            "id", "content_item_id", "content_hash", "created_at",
        }
        assert required.issubset(cols)

    def test_simhash_and_language(self, db_connection):
        cols = _column_names(db_connection, "item_versions")
        assert "simhash" in cols
        assert "language" in cols
        assert "normalized_text" in cols

    def test_dedup_group_link(self, db_connection):
        cols = _column_names(db_connection, "item_versions")
        assert "dedup_group_id" in cols

    def test_content_item_hash_unique(self, db_connection):
        uqs = _unique_constraints(db_connection, "item_versions")
        col_sets = [set(uq) for uq in uqs]
        assert {"content_item_id", "content_hash"} in col_sets


class TestDedupGroupsTable:
    """Tests for the dedup_groups table."""

    def test_table_exists(self, db_connection):
        assert "dedup_groups" in _table_names(db_connection)

    def test_columns(self, db_connection):
        cols = _column_names(db_connection, "dedup_groups")
        assert "id" in cols
        assert "canonical_item_version_id" in cols
        assert "created_at" in cols


class TestChunksTable:
    """Tests for the chunks table."""

    def test_table_exists(self, db_connection):
        assert "chunks" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "chunks")
        required = {
            "id", "item_version_id", "chunk_index", "text",
            "embedding_status", "created_at",
        }
        assert required.issubset(cols)

    def test_token_count_column(self, db_connection):
        cols = _column_names(db_connection, "chunks")
        assert "token_count" in cols

    def test_embedding_model_column(self, db_connection):
        cols = _column_names(db_connection, "chunks")
        assert "embedding_model" in cols

    def test_embedding_vector_column(self, db_connection):
        """Chunks should have a vector column for pgvector embeddings."""
        cols = _column_names(db_connection, "chunks")
        assert "embedding" in cols
