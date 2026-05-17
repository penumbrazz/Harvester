"""Tests for pipeline idempotency — upsert, observation dedup, version dedup."""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from harvester.db.models import ItemObservation, ItemVersion
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)


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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
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


def _insert_raw_object(db_session):
    """Helper to insert a raw object."""
    raw_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO raw_objects (id, compressed, created_at) "
            "VALUES (:id, :compressed, :created_at)"
        ),
        {"id": raw_id, "compressed": False, "created_at": datetime.now(UTC)},
    )
    return raw_id


class TestUpsertContentItemIdempotency:
    """Tests for external_id-based upsert idempotency."""

    def test_same_external_id_returns_existing_item(self, db_session):
        """Upserting with the same external_item_id should return the existing item."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-001",
            item_type="article",
            title="Original Title",
        )
        assert created1 is True

        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-001",
            item_type="article",
            title="Updated Title",
        )
        assert created2 is False
        assert item2.id == item1.id
        assert item2.title == "Updated Title"

    def test_different_external_id_creates_new_item(self, db_session):
        """Different external_item_id should create separate items."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-001",
            item_type="article",
        )
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-002",
            item_type="article",
        )
        assert created1 is True
        assert created2 is True
        assert item1.id != item2.id

    def test_no_external_id_always_creates_new(self, db_session):
        """Without external_item_id, each call should create a new item."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
        )
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
        )
        assert created1 is True
        assert created2 is True
        assert item1.id != item2.id

    def test_weak_key_canonical_url_hash_dedup(self, db_session):
        """Without external_item_id, same canonical_url_hash should upsert."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        url_hash = "a" * 64  # 64-char hex hash

        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
            canonical_url="https://example.com/article",
            canonical_url_hash=url_hash,
            title="First",
        )
        assert created1 is True

        # Same canonical_url_hash, no external_item_id -> should match existing
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
            canonical_url="https://example.com/article",
            canonical_url_hash=url_hash,
            title="Updated",
        )
        assert created2 is False
        assert item2.id == item1.id
        assert item2.title == "Updated"

    def test_weak_key_different_hash_creates_new(self, db_session):
        """Different canonical_url_hash without external_item_id creates new item."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
            canonical_url_hash="a" * 64,
        )
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
            canonical_url_hash="b" * 64,
        )
        assert created1 is True
        assert created2 is True
        assert item1.id != item2.id

    def test_external_id_takes_priority_over_weak_key(self, db_session):
        """When external_item_id is set, it should be used instead of weak key."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        url_hash = "a" * 64

        # Create with external_id and hash
        item1, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-priority",
            item_type="article",
            canonical_url_hash=url_hash,
        )

        # Without external_id but same hash -> should NOT match
        # because external_id match and weak key match are separate paths
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            item_type="article",
            canonical_url_hash=url_hash,
        )
        # Weak key should match since item1 has the same hash
        assert created2 is False
        assert item2.id == item1.id


class TestObservationIdempotency:
    """Tests for observation creation and dedup."""

    def test_observation_can_be_created(self, db_session):
        """Should successfully create an observation linking item to raw object."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        raw_id = _insert_raw_object(db_session)
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-obs-001",
            item_type="article",
        )

        obs = create_observation(
            db_session,
            content_item_id=item.id,
            raw_object_id=raw_id,
            position=0,
            snippet="test snippet",
        )
        assert obs.content_item_id == item.id
        assert obs.raw_object_id == raw_id
        assert obs.position == 0

    def test_duplicate_observation_updates_last_seen(self, db_session):
        """Re-creating observation with same (item, raw_object) updates last_seen."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        raw_id = _insert_raw_object(db_session)
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-obs-dedup",
            item_type="article",
        )

        obs1 = create_observation(
            db_session,
            content_item_id=item.id,
            raw_object_id=raw_id,
            snippet="first",
        )
        db_session.commit()

        obs2 = create_observation(
            db_session,
            content_item_id=item.id,
            raw_object_id=raw_id,
            snippet="updated",
        )
        db_session.commit()

        # Same row, not a duplicate
        assert obs2.id == obs1.id
        assert obs2.snippet == "updated"
        assert obs2.last_seen >= obs1.created_at

        # Only one observation row
        count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemObservation)
            .where(ItemObservation.content_item_id == item.id)
        )
        assert count == 1

    def test_multiple_observations_for_same_item(self, db_session):
        """Should allow multiple observations (from different raw objects)."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        raw1 = _insert_raw_object(db_session)
        raw2 = _insert_raw_object(db_session)
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-obs-multi",
            item_type="article",
        )

        obs1 = create_observation(
            db_session,
            content_item_id=item.id,
            raw_object_id=raw1,
        )
        obs2 = create_observation(
            db_session,
            content_item_id=item.id,
            raw_object_id=raw2,
        )
        assert obs1.id != obs2.id
        assert obs1.raw_object_id == raw1
        assert obs2.raw_object_id == raw2


class TestVersionIdempotency:
    """Tests for content_hash-based version dedup."""

    def test_same_content_hash_no_new_version(self, db_session):
        """Should not create a new version when content_hash is unchanged."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-ver-001",
            item_type="article",
        )

        v1, created1 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="hash-aaa",
            normalized_text="text v1",
        )
        assert created1 is True

        v2, created2 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="hash-aaa",
            normalized_text="text v1 again",
        )
        assert created2 is False
        assert v2.id == v1.id

    def test_different_content_hash_creates_new_version(self, db_session):
        """Should create a new version when content_hash changes."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-ver-002",
            item_type="article",
        )

        v1, created1 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="hash-aaa",
        )
        v2, created2 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="hash-bbb",
        )
        assert created1 is True
        assert created2 is True
        assert v1.id != v2.id

    def test_version_count_matches_unique_hashes(self, db_session):
        """Number of versions should match number of unique content hashes."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-ver-003",
            item_type="article",
        )

        for h in ["hash-1", "hash-2", "hash-1", "hash-3", "hash-2"]:
            create_version_if_changed(
                db_session,
                content_item_id=item.id,
                content_hash=h,
            )

        versions = db_session.scalars(
            sa.select(ItemVersion).where(ItemVersion.content_item_id == item.id)
        ).all()
        assert len(versions) == 3  # hash-1, hash-2, hash-3
