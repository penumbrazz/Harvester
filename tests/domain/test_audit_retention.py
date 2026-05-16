"""Tests for audit event retention configuration and cleanup.

Covers: default 7-day retention, env var override, invalid config rejection,
cutoff boundary, zero-delete on no expired events, and cleanup result fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import sqlalchemy as sa
import pytest

from harvester.domain.audit import write_audit
from harvester.domain.audit_retention import (
    DEFAULT_RETENTION_DAYS,
    CleanupResult,
    cleanup_audit_events,
    get_retention_days,
)


def _insert_audit(session, *, created_at: datetime) -> uuid.UUID:
    """Insert an audit event with a specific created_at timestamp."""
    event_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO audit_events "
            "(id, actor, action, entity_type, created_at) "
            "VALUES (:id, :actor, :action, :entity_type, :created_at)"
        ),
        {
            "id": event_id,
            "actor": "test",
            "action": "test.action",
            "entity_type": "source",
            "created_at": created_at,
        },
    )
    return event_id


class TestGetRetentionDays:
    """Tests for get_retention_days configuration reading."""

    def test_default_is_seven(self):
        """When env var is unset, default retention is 7 days."""
        with patch.dict("os.environ", {}, clear=True):
            # Make sure HARVESTER_AUDIT_RETENTION_DAYS is not set
            os_environ = __import__("os").environ
            os_environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            assert get_retention_days() == 7

    def test_env_var_override(self):
        """When HARVESTER_AUDIT_RETENTION_DAYS is set to a valid positive int, use it."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "30"}):
            assert get_retention_days() == 30

    def test_env_var_one(self):
        """Retention of 1 day is the minimum allowed value."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "1"}):
            assert get_retention_days() == 1

    def test_env_var_empty_uses_default(self):
        """Empty string falls back to default."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": ""}):
            assert get_retention_days() == 7

    def test_env_var_zero_rejected(self):
        """Zero is not a valid retention period."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "0"}):
            with pytest.raises(ValueError, match="must be >= 1"):
                get_retention_days()

    def test_env_var_negative_rejected(self):
        """Negative values are rejected."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "-5"}):
            with pytest.raises(ValueError, match="must be >= 1"):
                get_retention_days()

    def test_env_var_non_integer_rejected(self):
        """Non-integer values are rejected."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "abc"}):
            with pytest.raises(ValueError, match="must be a positive integer"):
                get_retention_days()

    def test_env_var_float_rejected(self):
        """Float strings are rejected (requires integer)."""
        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "3.5"}):
            with pytest.raises(ValueError, match="must be a positive integer"):
                get_retention_days()


class TestCleanupAuditEvents:
    """Tests for cleanup_audit_events core cleanup logic."""

    def test_deletes_expired_events(self, db_session):
        """Events older than retention window are deleted."""
        now = datetime.now(UTC)
        # Insert an event 10 days ago (beyond default 7-day window)
        old_id = _insert_audit(db_session, created_at=now - timedelta(days=10))
        # Insert a recent event (within window)
        recent_id = _insert_audit(db_session, created_at=now - timedelta(days=1))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 1
        assert result.retention_days == 7
        assert result.cutoff == now - timedelta(days=7)

        # Old event deleted, recent event kept
        remaining = (
            db_session.execute(sa.text("SELECT id FROM audit_events")).scalars().all()
        )
        assert recent_id in remaining
        assert old_id not in remaining

    def test_keeps_events_within_window(self, db_session):
        """Events within the retention window are preserved."""
        now = datetime.now(UTC)
        # Insert events 1 second inside the cutoff boundary
        inside_id = _insert_audit(
            db_session,
            created_at=now - timedelta(days=6, hours=23, minutes=59, seconds=59),
        )
        within_id = _insert_audit(db_session, created_at=now - timedelta(days=3))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 0
        remaining = set(
            db_session.execute(sa.text("SELECT id FROM audit_events")).scalars().all()
        )
        assert inside_id in remaining
        assert within_id in remaining

    def test_zero_delete_when_no_expired(self, db_session):
        """When no events are expired, deleted_count is 0."""
        now = datetime.now(UTC)
        _insert_audit(db_session, created_at=now - timedelta(days=1))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 0

    def test_zero_delete_when_table_empty(self, db_session):
        """Cleanup on an empty audit_events table returns 0."""
        now = datetime.now(UTC)

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 0
        assert result.retention_days == 7

    def test_custom_retention_days(self, db_session):
        """Cleanup respects HARVESTER_AUDIT_RETENTION_DAYS override."""
        now = datetime.now(UTC)
        # Insert event 5 days ago
        event_id = _insert_audit(db_session, created_at=now - timedelta(days=5))
        db_session.commit()

        with patch.dict("os.environ", {"HARVESTER_AUDIT_RETENTION_DAYS": "3"}):
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 1
        assert result.retention_days == 3
        assert result.cutoff == now - timedelta(days=3)

    def test_cutoff_boundary_exact(self, db_session):
        """Event exactly at cutoff is NOT deleted (< cutoff means older is deleted)."""
        now = datetime.now(UTC)
        retention = 7
        cutoff = now - timedelta(days=retention)

        # Event exactly at cutoff should be kept (DELETE uses < not <=)
        exact_id = _insert_audit(db_session, created_at=cutoff)
        # Event 1 second before cutoff should be deleted
        old_id = _insert_audit(db_session, created_at=cutoff - timedelta(seconds=1))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert result.deleted_count == 1
        remaining = set(
            db_session.execute(sa.text("SELECT id FROM audit_events")).scalars().all()
        )
        assert exact_id in remaining
        assert old_id not in remaining

    def test_result_is_cleanup_result_dataclass(self, db_session):
        """cleanup_audit_events returns a CleanupResult with required fields."""
        now = datetime.now(UTC)

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)

        assert isinstance(result, CleanupResult)
        assert hasattr(result, "deleted_count")
        assert hasattr(result, "cutoff")
        assert hasattr(result, "retention_days")


class TestCleanupDataSafety:
    """Audit cleanup must never delete business entities."""

    def test_preserves_source(self, db_session):
        """Cleanup does not delete source records."""
        from tests.utils.factories import insert_source

        now = datetime.now(UTC)
        source_id = insert_source(db_session, "safety-test-source")
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        _insert_audit(
            db_session,
            created_at=now - timedelta(days=10),
        )
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        remaining = db_session.execute(
            sa.text("SELECT id FROM sources WHERE id = :id"),
            {"id": str(source_id)},
        ).scalar()
        assert remaining is not None

    def test_preserves_recipe(self, db_session):
        """Cleanup does not delete recipe records."""
        now = datetime.now(UTC)
        rid = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO recipes "
                "(id, name, executor, risk_level, approval_status, version, created_at, updated_at) "
                "VALUES (:id, :name, 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
            ),
            {"id": rid, "name": "safety-recipe", "ts": now},
        )
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        remaining = db_session.execute(
            sa.text("SELECT id FROM recipes WHERE id = :id"),
            {"id": str(rid)},
        ).scalar()
        assert remaining is not None

    def test_preserves_schedule(self, db_session):
        """Cleanup does not delete watch_schedule records."""
        now = datetime.now(UTC)
        source_id = insert_source_by_sql(db_session, now)
        rid = insert_recipe_by_sql(db_session, now)
        sid = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO watch_schedules "
                "(id, schedule_key, source_id, recipe_id, status, "
                "interval_seconds, next_run_at, priority, created_at, updated_at) "
                "VALUES (:id, :key, :src, :recipe, 'active', 3600, :ts, 0, :ts, :ts)"
            ),
            {
                "id": sid,
                "key": f"source:{source_id}:recipe:{rid}",
                "src": source_id,
                "recipe": rid,
                "ts": now,
            },
        )
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        remaining = db_session.execute(
            sa.text("SELECT id FROM watch_schedules WHERE id = :id"),
            {"id": str(sid)},
        ).scalar()
        assert remaining is not None

    def test_preserves_crawl_run_and_raw_object(self, db_session):
        """Cleanup does not delete crawl_run or raw_object records."""
        from tests.utils.factories import insert_source

        now = datetime.now(UTC)
        source_id = insert_source(db_session, "safety-crawl-source")
        # Insert raw_object
        ro_id = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO raw_objects "
                "(id, source_id, content_type, content_hash, storage_uri, byte_size, "
                "retain_until, compressed, created_at) "
                "VALUES (:id, :src, 'text/html', :hash, 'file:///tmp/s.raw', 100, "
                ":retain, false, :ts)"
            ),
            {
                "id": ro_id,
                "src": source_id,
                "hash": uuid.uuid4().hex,
                "retain": now + timedelta(days=7),
                "ts": now,
            },
        )
        # Insert crawl_run
        cr_id = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO crawl_runs "
                "(id, source_id, raw_object_id, status, created_at) "
                "VALUES (:id, :src, :ro, 'completed', :ts)"
            ),
            {"id": cr_id, "src": source_id, "ro": ro_id, "ts": now},
        )
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert (
            db_session.execute(
                sa.text("SELECT id FROM raw_objects WHERE id = :id"), {"id": str(ro_id)}
            ).scalar()
            is not None
        )
        assert (
            db_session.execute(
                sa.text("SELECT id FROM crawl_runs WHERE id = :id"), {"id": str(cr_id)}
            ).scalar()
            is not None
        )

    def test_preserves_job(self, db_session):
        """Cleanup does not delete job records."""
        now = datetime.now(UTC)
        job_id = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO jobs "
                "(id, job_type, status, priority, attempts, max_attempts, lane, payload, "
                "created_at, updated_at) "
                "VALUES (:id, 'crawl', 'pending', 0, 0, 3, 'crawl', '{}', :ts, :ts)"
            ),
            {"id": job_id, "ts": now},
        )
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert (
            db_session.execute(
                sa.text("SELECT id FROM jobs WHERE id = :id"), {"id": str(job_id)}
            ).scalar()
            is not None
        )

    def test_preserves_content_item_version_chunk(self, db_session):
        """Cleanup does not delete content items, item versions, or chunks."""
        from tests.utils.factories import (
            insert_source,
            insert_content_item,
            insert_item_version,
            insert_chunk,
        )

        now = datetime.now(UTC)
        source_id = insert_source(db_session, "safety-content-source")
        ci_id = insert_content_item(db_session, source_id, "Safety Test Item")
        iv_id = insert_item_version(db_session, ci_id)
        chunk_id = insert_chunk(db_session, iv_id, 0, "safety test text")
        _insert_audit(db_session, created_at=now - timedelta(days=10))
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            cleanup_audit_events(db_session, now=now)
        db_session.commit()

        assert (
            db_session.execute(
                sa.text("SELECT id FROM content_items WHERE id = :id"),
                {"id": str(ci_id)},
            ).scalar()
            is not None
        )
        assert (
            db_session.execute(
                sa.text("SELECT id FROM item_versions WHERE id = :id"),
                {"id": str(iv_id)},
            ).scalar()
            is not None
        )
        assert (
            db_session.execute(
                sa.text("SELECT id FROM chunks WHERE id = :id"), {"id": str(chunk_id)}
            ).scalar()
            is not None
        )


def insert_source_by_sql(session, now) -> uuid.UUID:
    """Insert a source row for data safety tests."""
    sid = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, created_at, updated_at) "
            "VALUES (:id, :name, 'web', 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {"id": sid, "name": f"safety-src-{sid.hex[:6]}", "ts": now},
    )
    return sid


class TestArchivedRecordRetention:
    """Verify archived business records are preserved while their audit events
    follow the retention policy and can be cleaned up."""

    def test_archived_source_preserved_after_audit_cleanup(self, db_session):
        """Archived source record is preserved even after its audit events expire."""
        from tests.utils.factories import insert_source

        now = datetime.now(UTC)
        source_id = insert_source(db_session, "to-be-archived")
        # Archive the source (status change)
        db_session.execute(
            sa.text("UPDATE sources SET status = 'archived' WHERE id = :id"),
            {"id": str(source_id)},
        )
        # Insert an expired audit event referencing this source
        db_session.execute(
            sa.text(
                "INSERT INTO audit_events "
                "(id, actor, action, entity_type, entity_id, created_at) "
                "VALUES (:id, 'admin', 'status_change', 'source', :eid, :ts)"
            ),
            {
                "id": uuid.uuid4(),
                "eid": str(source_id),
                "ts": now - timedelta(days=10),
            },
        )
        db_session.commit()

        with patch.dict("os.environ", {}, clear=False):
            __import__("os").environ.pop("HARVESTER_AUDIT_RETENTION_DAYS", None)
            result = cleanup_audit_events(db_session, now=now)
        db_session.commit()

        # Audit event expired and was cleaned up
        assert result.deleted_count == 1
        # Source record still exists with archived status
        row = db_session.execute(
            sa.text("SELECT status FROM sources WHERE id = :id"),
            {"id": str(source_id)},
        ).fetchone()
        assert row is not None
        assert row[0] == "archived"


def insert_recipe_by_sql(session, now) -> uuid.UUID:
    """Insert a recipe row for data safety tests."""
    rid = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO recipes "
            "(id, name, executor, risk_level, approval_status, version, created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": rid, "name": f"safety-recipe-{rid.hex[:6]}", "ts": now},
    )
    return rid
