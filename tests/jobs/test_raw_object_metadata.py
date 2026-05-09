"""Tests for raw object metadata creation."""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from harvester.db.models import RawObject


def _insert_source(db_session, **overrides):
    """Helper to insert a source directly."""
    source_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=source_id,
        name=f"test-source-{source_id.hex[:8]}",
        kind="rss",
        status="active",
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    db_session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES "
            "(:id, :name, :kind, :status, :trust_level, :auth_required, :failure_count, "
            ":created_at, :updated_at)"
        ),
        defaults,
    )
    return source_id


class TestRawObjectMetadata:
    """Tests for raw object metadata persistence."""

    def test_create_raw_object_with_metadata(self, db_session):
        """Should persist a raw object with all metadata fields."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        raw_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        db_session.execute(
            sa.text(
                "INSERT INTO raw_objects "
                "(id, source_id, content_type, content_hash, storage_uri, "
                "byte_size, retention_policy, retain_until, compressed, created_at) "
                "VALUES "
                "(:id, :source_id, :content_type, :content_hash, :storage_uri, "
                ":byte_size, :retention_policy, :retain_until, :compressed, :created_at)"
            ),
            {
                "id": raw_id,
                "source_id": source_id,
                "content_type": "text/html",
                "content_hash": "sha256:abcdef1234567890",
                "storage_uri": "s3://bucket/raw/test.html",
                "byte_size": 4096,
                "retention_policy": None,
                "retain_until": None,
                "compressed": False,
                "created_at": now,
            },
        )
        db_session.commit()

        raw_obj = db_session.get(RawObject, raw_id)
        assert raw_obj is not None
        assert raw_obj.source_id == source_id
        assert raw_obj.content_type == "text/html"
        assert raw_obj.content_hash == "sha256:abcdef1234567890"
        assert raw_obj.storage_uri == "s3://bucket/raw/test.html"
        assert raw_obj.byte_size == 4096
        assert raw_obj.compressed is False

    def test_raw_object_default_values(self, db_session):
        """Raw object should have sensible defaults for optional fields."""
        raw_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        db_session.execute(
            sa.text(
                "INSERT INTO raw_objects (id, compressed, created_at) "
                "VALUES (:id, :compressed, :created_at)"
            ),
            {"id": raw_id, "compressed": False, "created_at": now},
        )
        db_session.commit()

        raw_obj = db_session.get(RawObject, raw_id)
        assert raw_obj is not None
        assert raw_obj.source_id is None
        assert raw_obj.content_type is None
        assert raw_obj.content_hash is None
        assert raw_obj.storage_uri is None
        assert raw_obj.byte_size is None
        assert raw_obj.retention_policy is None
        assert raw_obj.retain_until is None
        assert raw_obj.compressed is False

    def test_raw_object_with_retention_policy(self, db_session):
        """Should store retention policy and deadline."""
        raw_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        retain_until = now + __import__("datetime").timedelta(days=7)
        db_session.execute(
            sa.text(
                "INSERT INTO raw_objects "
                "(id, retention_policy, retain_until, compressed, created_at) "
                "VALUES (:id, :retention_policy, :retain_until, :compressed, :created_at)"
            ),
            {
                "id": raw_id,
                "retention_policy": "extracted",
                "retain_until": retain_until,
                "compressed": False,
                "created_at": now,
            },
        )
        db_session.commit()

        raw_obj = db_session.get(RawObject, raw_id)
        assert raw_obj.retention_policy == "extracted"
        assert raw_obj.retain_until is not None
        assert raw_obj.retain_until > now

    def test_multiple_raw_objects_for_same_source(self, db_session):
        """Should allow multiple raw objects for the same source."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        now = datetime.now(timezone.utc)
        ids = [uuid.uuid4() for _ in range(3)]
        for raw_id in ids:
            db_session.execute(
                sa.text(
                    "INSERT INTO raw_objects "
                    "(id, source_id, compressed, created_at) "
                    "VALUES (:id, :source_id, :compressed, :created_at)"
                ),
                {
                    "id": raw_id,
                    "source_id": source_id,
                    "compressed": False,
                    "created_at": now,
                },
            )
        db_session.commit()

        objects = db_session.scalars(
            sa.select(RawObject).where(RawObject.source_id == source_id)
        ).all()
        assert len(objects) == 3
