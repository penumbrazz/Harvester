"""Tests for crawl_targets schema."""

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
            "WHERE attrelid = :table_oid AND attnum > 0 AND NOT attisdropped"
        ),
        {"table_oid": _table_oid(conn, table_name)},
    )
    return {row[0] for row in result}


def _table_oid(conn, table_name: str) -> int:
    result = conn.execute(
        sa.text(
            "SELECT oid FROM pg_class "
            "WHERE relname = :name AND relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public')"
        ),
        {"name": table_name},
    )
    row = result.fetchone()
    return row[0] if row else 0


def _foreign_keys(conn, table_name: str) -> dict[str, str]:
    result = conn.execute(
        sa.text(
            "SELECT kcu.column_name, ccu.table_name AS referred_table "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name = kcu.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON tc.constraint_name = ccu.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' "
            "  AND tc.table_name = :table AND tc.table_schema = 'public'"
        ),
        {"table": table_name},
    )
    return {row[0]: row[1] for row in result}


def _unique_constraints(conn, table_name: str) -> set[str]:
    result = conn.execute(
        sa.text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = :table "
            "AND constraint_type = 'UNIQUE'"
        ),
        {"table": table_name},
    )
    return {row[0] for row in result}


def _index_names(conn, table_name: str) -> set[str]:
    result = conn.execute(
        sa.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = :table"
        ),
        {"table": table_name},
    )
    return {row[0] for row in result}


class TestCrawlTargetsTable:
    """Tests for discovered crawl target persistence schema."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "crawl_targets" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "crawl_targets")
        required = {
            "id",
            "source_id",
            "recipe_id",
            "parent_target_id",
            "discovered_from_raw_object_id",
            "target_url",
            "final_url",
            "canonical_url",
            "canonical_url_hash",
            "target_role",
            "media_type",
            "external_item_id",
            "status",
            "depth",
            "priority",
            "last_raw_object_id",
            "failure_count",
            "last_error",
            "first_seen_at",
            "last_seen_at",
            "created_at",
            "updated_at",
        }
        assert required.issubset(cols)

    def test_foreign_keys(self, db_connection):
        fks = _foreign_keys(db_connection, "crawl_targets")
        assert fks["source_id"] == "sources"
        assert fks["recipe_id"] == "recipes"
        assert fks["parent_target_id"] == "crawl_targets"
        assert fks["discovered_from_raw_object_id"] == "raw_objects"
        assert fks["last_raw_object_id"] == "raw_objects"

    def test_source_role_canonical_unique_key(self, db_connection):
        constraints = _unique_constraints(db_connection, "crawl_targets")
        assert "uq_crawl_targets_source_role_canonical" in constraints

    def test_common_query_indexes(self, db_connection):
        indexes = _index_names(db_connection, "crawl_targets")
        expected = {
            "ix_crawl_targets_source_status",
            "ix_crawl_targets_parent_target_id",
            "ix_crawl_targets_last_seen_at",
            "ix_crawl_targets_external_item_id",
        }
        assert expected.issubset(indexes)
