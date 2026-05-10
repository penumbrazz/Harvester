"""Tests for the watch_schedules table schema.

Covers: table existence, column types, unique schedule_key constraint,
foreign keys to sources/topic_watches/recipes, interval_seconds,
next_run_at, status, and the (status, next_run_at) index.
"""

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session


def _insert_recipe(session: Session) -> uuid.UUID:
    """Insert a recipe row and return its id."""
    rid = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, "
            "created_at, updated_at) "
            "VALUES (:id, 'test_recipe', 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": rid, "ts": datetime.now(timezone.utc)},
    )
    return rid


def _insert_source(session: Session) -> uuid.UUID:
    """Insert a source row and return its id."""
    sid = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES (:id, :name, 'rss', 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {"id": sid, "name": f"src_{sid.hex[:8]}", "ts": datetime.now(timezone.utc)},
    )
    return sid


def _insert_topic(session: Session) -> uuid.UUID:
    """Insert a topic_watch row and return its id."""
    tid = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO topic_watches (id, name, status, created_at, updated_at) "
            "VALUES (:id, :name, 'active', :ts, :ts)"
        ),
        {"id": tid, "name": f"topic_{tid.hex[:8]}", "ts": datetime.now(timezone.utc)},
    )
    return tid


class TestWatchSchedulesSchema:
    """Verify the watch_schedules table structure and constraints."""

    def test_table_exists(self, db_connection):
        """The watch_schedules table must exist."""
        result = db_connection.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_name = 'watch_schedules'"
                ")"
            )
        )
        assert result.scalar() is True

    def test_required_columns(self, db_connection):
        """All required columns must exist with correct types."""
        expected = {
            "id": "uuid",
            "schedule_key": "character varying",
            "source_id": "uuid",
            "topic_watch_id": "uuid",
            "recipe_id": "uuid",
            "status": "character varying",
            "interval_seconds": "integer",
            "next_run_at": "timestamp with time zone",
            "last_enqueued_at": "timestamp with time zone",
            "priority": "integer",
            "lane": "character varying",
            "created_at": "timestamp with time zone",
            "updated_at": "timestamp with time zone",
        }
        result = db_connection.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'watch_schedules' "
                "ORDER BY column_name"
            )
        )
        columns = {row[0]: row[1] for row in result.fetchall()}
        for col_name, col_type in expected.items():
            assert col_name in columns, f"Missing column: {col_name}"
            assert columns[col_name] == col_type, (
                f"Column {col_name}: expected {col_type}, got {columns[col_name]}"
            )

    def test_unique_schedule_key(self, db_connection):
        """schedule_key must have a unique constraint."""
        src = _insert_source(db_connection)
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        key = "source:test:unique"

        db_connection.execute(
            text(
                "INSERT INTO watch_schedules "
                "(id, schedule_key, source_id, recipe_id, status, "
                "interval_seconds, next_run_at, created_at, updated_at) "
                "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, :ts, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "key": key,
                "src": src,
                "recipe": recipe,
                "ts": now,
            },
        )
        # Duplicate schedule_key should fail
        with pytest.raises(Exception, match="unique|duplicate"):
            db_connection.execute(
                text(
                    "INSERT INTO watch_schedules "
                    "(id, schedule_key, source_id, recipe_id, status, "
                    "interval_seconds, next_run_at, created_at, updated_at) "
                    "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, :ts, :ts)"
                ),
                {
                    "id": uuid.uuid4(),
                    "key": key,
                    "src": src,
                    "recipe": recipe,
                    "ts": now,
                },
            )
            db_connection.commit()

    def test_foreign_key_source(self, db_connection):
        """source_id must reference sources.id."""
        fake_id = uuid.uuid4()
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        with pytest.raises(Exception, match="foreign|violates|constraint"):
            db_connection.execute(
                text(
                    "INSERT INTO watch_schedules "
                    "(id, schedule_key, source_id, recipe_id, status, "
                    "interval_seconds, next_run_at, created_at, updated_at) "
                    "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, :ts, :ts)"
                ),
                {
                    "id": uuid.uuid4(),
                    "key": "fk_test_source",
                    "src": fake_id,
                    "recipe": recipe,
                    "ts": now,
                },
            )
            db_connection.commit()

    def test_foreign_key_recipe(self, db_connection):
        """recipe_id must reference recipes.id."""
        src = _insert_source(db_connection)
        fake_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        with pytest.raises(Exception, match="foreign|violates|constraint"):
            db_connection.execute(
                text(
                    "INSERT INTO watch_schedules "
                    "(id, schedule_key, source_id, recipe_id, status, "
                    "interval_seconds, next_run_at, created_at, updated_at) "
                    "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, :ts, :ts)"
                ),
                {
                    "id": uuid.uuid4(),
                    "key": "fk_test_recipe",
                    "src": src,
                    "recipe": fake_id,
                    "ts": now,
                },
            )
            db_connection.commit()

    def test_foreign_key_topic_watch(self, db_connection):
        """topic_watch_id must reference topic_watches.id when provided."""
        fake_id = uuid.uuid4()
        src = _insert_source(db_connection)
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        with pytest.raises(Exception, match="foreign|violates|constraint"):
            db_connection.execute(
                text(
                    "INSERT INTO watch_schedules "
                    "(id, schedule_key, source_id, topic_watch_id, recipe_id, "
                    "status, interval_seconds, next_run_at, created_at, updated_at) "
                    "VALUES (:id, :key, :src, :topic, :recipe, 'active', 3600, :ts, :ts, :ts)"
                ),
                {
                    "id": uuid.uuid4(),
                    "key": "fk_test_topic",
                    "src": src,
                    "topic": fake_id,
                    "recipe": recipe,
                    "ts": now,
                },
            )
            db_connection.commit()

    def test_topic_watch_nullable(self, db_connection):
        """topic_watch_id can be null (source-only schedule)."""
        src = _insert_source(db_connection)
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        db_connection.execute(
            text(
                "INSERT INTO watch_schedules "
                "(id, schedule_key, source_id, recipe_id, status, "
                "interval_seconds, next_run_at, created_at, updated_at) "
                "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, :ts, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "key": "nullable_topic_test",
                "src": src,
                "recipe": recipe,
                "ts": now,
            },
        )
        # Should succeed without error
        result = db_connection.execute(
            text(
                "SELECT topic_watch_id FROM watch_schedules "
                "WHERE schedule_key = 'nullable_topic_test'"
            )
        )
        assert result.scalar() is None

    def test_status_next_run_at_index(self, db_connection):
        """There should be an index on (status, next_run_at) for scheduler queries."""
        result = db_connection.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = 'watch_schedules'"
            )
        )
        indexes = {row[0]: row[1] for row in result.fetchall()}
        # Check for composite index on status, next_run_at
        found = any(
            "status" in defn.lower() and "next_run_at" in defn.lower()
            for defn in indexes.values()
        )
        assert found, (
            f"No index found on (status, next_run_at). "
            f"Existing indexes: {list(indexes.keys())}"
        )

    def test_default_status(self, db_connection):
        """status column should default to 'active'."""
        src = _insert_source(db_connection)
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        db_connection.execute(
            text(
                "INSERT INTO watch_schedules "
                "(id, schedule_key, source_id, recipe_id, "
                "interval_seconds, next_run_at, created_at, updated_at) "
                "VALUES (:id, :key, :src, :recipe, 3600, :ts, :ts, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "key": "default_status_test",
                "src": src,
                "recipe": recipe,
                "ts": now,
            },
        )
        result = db_connection.execute(
            text(
                "SELECT status FROM watch_schedules "
                "WHERE schedule_key = 'default_status_test'"
            )
        )
        assert result.scalar() == "active"

    def test_default_priority(self, db_connection):
        """priority column should default to 0."""
        src = _insert_source(db_connection)
        recipe = _insert_recipe(db_connection)
        now = datetime.now(timezone.utc)
        db_connection.execute(
            text(
                "INSERT INTO watch_schedules "
                "(id, schedule_key, source_id, recipe_id, "
                "interval_seconds, next_run_at, created_at, updated_at) "
                "VALUES (:id, :key, :src, :recipe, 3600, :ts, :ts, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "key": "default_priority_test",
                "src": src,
                "recipe": recipe,
                "ts": now,
            },
        )
        result = db_connection.execute(
            text(
                "SELECT priority FROM watch_schedules "
                "WHERE schedule_key = 'default_priority_test'"
            )
        )
        assert result.scalar() == 0
