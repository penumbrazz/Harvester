"""Tests for core schema: sources, topic_watches, topic_sources, recipes, crawl_runs, raw_objects."""

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


def _foreign_keys(conn, table_name: str) -> list[dict]:
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
    return [{"column": row[0], "referred_table": row[1]} for row in result]


class TestSourcesTable:
    """Tests for the sources table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "sources" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "sources")
        required = {
            "id",
            "name",
            "kind",
            "status",
            "trust_level",
            "auth_required",
            "failure_count",
            "created_at",
            "updated_at",
        }
        assert required.issubset(cols)

    def test_default_recipe_fk(self, db_connection):
        fks = _foreign_keys(db_connection, "sources")
        fk_cols = {fk["column"] for fk in fks}
        assert "default_recipe_id" in fk_cols

    def test_optional_url_column(self, db_connection):
        cols = _column_names(db_connection, "sources")
        assert "url" in cols


class TestTopicWatchesTable:
    """Tests for the topic_watches table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "topic_watches" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "topic_watches")
        required = {
            "id",
            "name",
            "status",
            "ttl_seconds",
            "created_at",
            "updated_at",
        }
        assert required.issubset(cols)


class TestTopicSourcesTable:
    """Tests for the topic_sources association table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "topic_sources" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "topic_sources")
        required = {"id", "topic_watch_id", "source_id", "created_at"}
        assert required.issubset(cols)

    def test_foreign_keys(self, db_connection):
        fks = _foreign_keys(db_connection, "topic_sources")
        fk_cols = {fk["column"] for fk in fks}
        assert "topic_watch_id" in fk_cols
        assert "source_id" in fk_cols


class TestRecipesTable:
    """Tests for the recipes table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "recipes" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "recipes")
        required = {
            "id",
            "name",
            "executor",
            "config",
            "risk_level",
            "approval_status",
            "version",
            "created_at",
            "updated_at",
        }
        assert required.issubset(cols)

    def test_auth_profile_column(self, db_connection):
        cols = _column_names(db_connection, "recipes")
        assert "auth_profile" in cols


class TestCrawlRunsTable:
    """Tests for the crawl_runs table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "crawl_runs" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "crawl_runs")
        required = {
            "id",
            "status",
            "started_at",
            "completed_at",
            "created_at",
        }
        assert required.issubset(cols)

    def test_reference_columns(self, db_connection):
        cols = _column_names(db_connection, "crawl_runs")
        refs = {"source_id", "topic_watch_id", "recipe_id", "raw_object_id"}
        assert refs.issubset(cols)

    def test_http_metadata_columns(self, db_connection):
        cols = _column_names(db_connection, "crawl_runs")
        assert "http_status" in cols
        assert "content_type" in cols

    def test_error_fields(self, db_connection):
        cols = _column_names(db_connection, "crawl_runs")
        assert "error_message" in cols


class TestRawObjectsTable:
    """Tests for the raw_objects table."""

    def test_table_exists(self, db_connection):
        tables = _table_names(db_connection)
        assert "raw_objects" in tables

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "raw_objects")
        required = {
            "id",
            "content_hash",
            "storage_uri",
            "created_at",
        }
        assert required.issubset(cols)

    def test_retention_columns(self, db_connection):
        cols = _column_names(db_connection, "raw_objects")
        assert "retention_policy" in cols
        assert "retain_until" in cols

    def test_no_payload_blob_column(self, db_connection):
        """raw_objects should NOT have an inline payload/blob column."""
        cols = _column_names(db_connection, "raw_objects")
        assert "payload" not in cols
        assert "body" not in cols
        assert "content" not in cols
        assert "data" not in cols
