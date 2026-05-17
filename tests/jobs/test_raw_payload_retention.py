"""Tests for raw payload retention logic."""

import uuid
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from harvester.db.models import RawObject
from harvester.jobs.retention import (
    DEFAULT_RETENTION_DAYS,
    cleanup_expired_payloads,
    mark_raw_object_extracted,
)


def _insert_raw_object(db_session, **overrides):
    """Helper to insert a raw object directly."""
    raw_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=raw_id,
        content_type="text/html",
        content_hash="sha256:test",
        storage_uri="s3://bucket/test.html",
        byte_size=1024,
        retention_policy=None,
        retain_until=None,
        compressed=False,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    columns = ", ".join(defaults.keys())
    placeholders = ", ".join(f":{k}" for k in defaults.keys())
    db_session.execute(
        sa.text(f"INSERT INTO raw_objects ({columns}) VALUES ({placeholders})"),
        defaults,
    )
    return raw_id


class TestMarkRawObjectExtracted:
    """Tests for the mark_raw_object_extracted function."""

    def test_sets_retention_policy(self, db_session):
        """Should set retention_policy to 'extracted'."""
        raw_id = _insert_raw_object(db_session, id=uuid.uuid4())
        db_session.commit()

        mark_raw_object_extracted(db_session, raw_id)

        raw_obj = db_session.get(RawObject, raw_id)
        assert raw_obj.retention_policy == "extracted"

    def test_sets_retain_until_deadline(self, db_session):
        """Should set retain_until to now + DEFAULT_RETENTION_DAYS."""
        raw_id = _insert_raw_object(db_session, id=uuid.uuid4())
        db_session.commit()

        before = datetime.now(UTC)
        mark_raw_object_extracted(db_session, raw_id)
        after = datetime.now(UTC)

        raw_obj = db_session.get(RawObject, raw_id)
        assert raw_obj.retain_until is not None

        expected_min = before + timedelta(days=DEFAULT_RETENTION_DAYS)
        expected_max = after + timedelta(days=DEFAULT_RETENTION_DAYS)
        assert expected_min <= raw_obj.retain_until <= expected_max

    def test_raises_for_nonexistent_raw_object(self, db_session):
        """Should raise ValueError for a nonexistent raw object."""
        fake_id = uuid.uuid4()
        import pytest

        with pytest.raises(ValueError, match="not found"):
            mark_raw_object_extracted(db_session, fake_id)


class TestCleanupExpiredPayloads:
    """Tests for the cleanup_expired_payloads function."""

    def test_returns_expired_objects(self, db_session):
        """Should return raw objects whose retain_until has passed."""
        past = datetime.now(UTC) - timedelta(days=1)
        expired_id = _insert_raw_object(
            db_session,
            id=uuid.uuid4(),
            retention_policy="extracted",
            retain_until=past,
        )
        db_session.commit()

        expired = cleanup_expired_payloads(db_session)
        assert any(o.id == expired_id for o in expired)

    def test_skips_non_expired_objects(self, db_session):
        """Should not return raw objects whose retain_until is in the future."""
        future = datetime.now(UTC) + timedelta(days=7)
        _insert_raw_object(
            db_session,
            id=uuid.uuid4(),
            retention_policy="extracted",
            retain_until=future,
        )
        db_session.commit()

        expired = cleanup_expired_payloads(db_session)
        assert len(expired) == 0

    def test_skips_objects_without_retain_until(self, db_session):
        """Should not return raw objects that have no retain_until set."""
        _insert_raw_object(db_session, id=uuid.uuid4())
        db_session.commit()

        expired = cleanup_expired_payloads(db_session)
        assert len(expired) == 0

    def test_mixed_expired_and_valid(self, db_session):
        """Should only return expired objects when mixing both."""
        past = datetime.now(UTC) - timedelta(days=1)
        future = datetime.now(UTC) + timedelta(days=7)

        expired_id = _insert_raw_object(
            db_session,
            id=uuid.uuid4(),
            retention_policy="extracted",
            retain_until=past,
        )
        _insert_raw_object(
            db_session,
            id=uuid.uuid4(),
            retention_policy="extracted",
            retain_until=future,
        )
        db_session.commit()

        expired = cleanup_expired_payloads(db_session)
        assert len(expired) == 1
        assert expired[0].id == expired_id

    def test_does_not_delete_records(self, db_session):
        """Cleanup should only list expired objects, not delete them."""
        past = datetime.now(UTC) - timedelta(days=1)
        expired_id = _insert_raw_object(
            db_session,
            id=uuid.uuid4(),
            retention_policy="extracted",
            retain_until=past,
        )
        db_session.commit()

        cleanup_expired_payloads(db_session)

        # Record should still exist
        raw_obj = db_session.get(RawObject, expired_id)
        assert raw_obj is not None
