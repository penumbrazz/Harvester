"""Tests for jobs, source_frontiers and audit_events schema."""

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


def _index_names(conn, table_name: str) -> set[str]:
    result = conn.execute(
        sa.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = :table"
        ),
        {"table": table_name},
    )
    return {row[0] for row in result}


class TestJobsTable:
    """Tests for the jobs table."""

    def test_table_exists(self, db_connection):
        assert "jobs" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "jobs")
        required = {
            "id", "job_type", "status", "priority",
            "attempts", "max_attempts", "payload", "created_at", "updated_at",
        }
        assert required.issubset(cols)

    def test_lease_columns(self, db_connection):
        cols = _column_names(db_connection, "jobs")
        assert "locked_by" in cols
        assert "locked_until" in cols

    def test_run_after_column(self, db_connection):
        cols = _column_names(db_connection, "jobs")
        assert "run_after" in cols

    def test_idempotency_key_column(self, db_connection):
        cols = _column_names(db_connection, "jobs")
        assert "idempotency_key" in cols

    def test_last_error_column(self, db_connection):
        cols = _column_names(db_connection, "jobs")
        assert "last_error" in cols

    def test_status_priority_index(self, db_connection):
        indexes = _index_names(db_connection, "jobs")
        assert any("status" in idx and "priority" in idx for idx in indexes)

    def test_locked_until_index(self, db_connection):
        indexes = _index_names(db_connection, "jobs")
        assert any("locked_until" in idx for idx in indexes)


class TestSourceFrontiersTable:
    """Tests for the source_frontiers table."""

    def test_table_exists(self, db_connection):
        assert "source_frontiers" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "source_frontiers")
        required = {
            "id", "source_id", "cursor_value", "updated_at",
        }
        assert required.issubset(cols)

    def test_frontier_json_column(self, db_connection):
        cols = _column_names(db_connection, "source_frontiers")
        assert "frontier_state" in cols

    def test_rewind_window_column(self, db_connection):
        cols = _column_names(db_connection, "source_frontiers")
        assert "rewind_window" in cols

    def test_last_complete_range_column(self, db_connection):
        cols = _column_names(db_connection, "source_frontiers")
        assert "last_complete_range" in cols


class TestAuditEventsTable:
    """Tests for the audit_events table."""

    def test_table_exists(self, db_connection):
        assert "audit_events" in _table_names(db_connection)

    def test_required_columns(self, db_connection):
        cols = _column_names(db_connection, "audit_events")
        required = {
            "id", "actor", "action", "entity_type", "created_at",
        }
        assert required.issubset(cols)

    def test_state_columns(self, db_connection):
        cols = _column_names(db_connection, "audit_events")
        assert "before_state" in cols
        assert "after_state" in cols

    def test_reason_column(self, db_connection):
        cols = _column_names(db_connection, "audit_events")
        assert "reason" in cols

    def test_entity_index(self, db_connection):
        indexes = _index_names(db_connection, "audit_events")
        assert any("entity" in idx for idx in indexes)

    def test_created_at_index(self, db_connection):
        indexes = _index_names(db_connection, "audit_events")
        assert any("created_at" in idx for idx in indexes)
