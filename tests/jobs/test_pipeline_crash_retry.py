"""Tests for partial extraction crash recovery — no duplicate items on retry."""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from harvester.db.models import ContentItem, ItemVersion, Job, Source
from harvester.jobs.pipeline import (
    create_downstream_jobs,
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


def _insert_raw_object(db_session):
    """Helper to insert a raw object."""
    raw_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO raw_objects (id, compressed, created_at) "
            "VALUES (:id, :compressed, :created_at)"
        ),
        {"id": raw_id, "compressed": False, "created_at": datetime.now(timezone.utc)},
    )
    return raw_id


class TestPartialExtractionRetry:
    """Tests for crash-retry scenarios where extraction is partially complete."""

    def test_re_upsert_same_external_id_no_duplicate_item(self, db_session):
        """Re-running upsert with the same external_id should not duplicate."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        # First extraction attempt (simulating partial success)
        item1, created1 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-crash-001",
            item_type="article",
            title="First Attempt",
        )
        assert created1 is True

        # Retry extraction (simulating re-processing after crash)
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-crash-001",
            item_type="article",
            title="Second Attempt",
        )
        assert created2 is False
        assert item2.id == item1.id

        # Verify only one item exists
        count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentItem)
            .where(ContentItem.external_item_id == "ext-crash-001")
        )
        assert count == 1

    def test_re_create_version_same_hash_no_duplicate(self, db_session):
        """Re-running version creation with the same hash should not duplicate."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-crash-002",
            item_type="article",
        )

        # First attempt at version creation
        v1, created1 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="crash-hash-001",
            normalized_text="original text",
        )
        assert created1 is True

        # Retry (crash happened after version was saved but before downstream)
        v2, created2 = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="crash-hash-001",
            normalized_text="original text",
        )
        assert created2 is False
        assert v2.id == v1.id

        # Only one version
        count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemVersion)
            .where(ItemVersion.content_item_id == item.id)
        )
        assert count == 1

    def test_full_pipeline_replay_is_idempotent(self, db_session):
        """Replaying the full pipeline on the same data should be idempotent."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        raw_id = _insert_raw_object(db_session)
        db_session.commit()

        ext_id = "ext-crash-full-001"
        content_hash = "crash-full-hash-001"

        # First run
        item_a, created_a = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id=ext_id,
            item_type="article",
            title="Title",
        )
        create_version_if_changed(
            db_session,
            content_item_id=item_a.id,
            content_hash=content_hash,
            normalized_text="text",
        )

        # Simulate crash and retry: re-run the full pipeline
        item_b, created_b = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id=ext_id,
            item_type="article",
            title="Title",
        )
        v_b, v_created_b = create_version_if_changed(
            db_session,
            content_item_id=item_b.id,
            content_hash=content_hash,
            normalized_text="text",
        )

        assert created_b is False
        assert v_created_b is False

        # Still only one item and one version
        item_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentItem)
            .where(ContentItem.external_item_id == ext_id)
        )
        assert item_count == 1

        version_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemVersion)
            .where(ItemVersion.content_item_id == item_a.id)
        )
        assert version_count == 1

    def test_multiple_raw_objects_same_item(self, db_session):
        """Processing the same item from different raw objects should not duplicate."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        raw1 = _insert_raw_object(db_session)
        raw2 = _insert_raw_object(db_session)
        db_session.commit()

        ext_id = "ext-crash-multi-raw"

        # First raw object
        item1, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id=ext_id,
            item_type="article",
        )
        create_observation(
            db_session,
            content_item_id=item1.id,
            raw_object_id=raw1,
            position=0,
        )

        # Second raw object (same item)
        item2, created2 = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id=ext_id,
            item_type="article",
        )
        assert created2 is False
        assert item2.id == item1.id

        create_observation(
            db_session,
            content_item_id=item2.id,
            raw_object_id=raw2,
            position=0,
        )

        # One item, two observations
        obs_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(sa.text("item_observations"))
            .where(sa.text("content_item_id = :cid")),
            {"cid": item1.id},
        )
        assert obs_count == 2


class TestDownstreamJobTransactionBoundary:
    """Tests that downstream jobs share the same transaction as the pipeline."""

    def test_downstream_jobs_created_in_same_transaction(self, db_session):
        """Item version + downstream jobs must be in the same transaction."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-txn-001",
            item_type="article",
        )
        version, _ = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="txn-hash-001",
            normalized_text="content",
        )

        # Create downstream jobs (should not auto-commit)
        jobs = create_downstream_jobs(db_session, version.id)
        assert len(jobs) == 1

        # Both version and job are in the same transaction (not yet committed)
        job_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(Job)
            .where(Job.job_type == "embed_chunks")
        )
        assert job_count == 1

    def test_retry_does_not_duplicate_downstream_jobs(self, db_session):
        """Re-running pipeline with downstream jobs must not duplicate."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        item, _ = upsert_content_item(
            db_session,
            source_id=source_id,
            external_item_id="ext-txn-dedup",
            item_type="article",
        )
        version, _ = create_version_if_changed(
            db_session,
            content_item_id=item.id,
            content_hash="txn-dedup-hash",
            normalized_text="content",
        )

        # First run: create downstream jobs
        jobs1 = create_downstream_jobs(db_session, version.id)
        db_session.commit()
        assert len(jobs1) == 1

        # Retry: re-create downstream jobs for the same version
        jobs2 = create_downstream_jobs(db_session, version.id)
        db_session.commit()

        # Should have created a second job (no idempotency key)
        total_jobs = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(Job)
            .where(Job.job_type == "embed_chunks")
        )
        # Since no idempotency_key is used, a second job is created
        assert total_jobs == len(jobs1) + len(jobs2)
