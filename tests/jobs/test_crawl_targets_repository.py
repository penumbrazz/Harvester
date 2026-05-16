"""Tests for crawl target repository helpers."""

import uuid
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from harvester.db.models import CrawlTarget
from harvester.jobs.crawl_targets import (
    create_crawl_job_for_target,
    find_crawl_target,
    list_crawl_targets,
    upsert_crawl_target,
)
from tests.utils.factories import insert_source


def _insert_recipe(session, name: str = "cdc-discovery") -> uuid.UUID:
    recipe_id = uuid.uuid4()
    now = datetime.now(UTC)
    session.execute(
        sa.text(
            "INSERT INTO recipes "
            "(id, name, executor, config, risk_level, approval_status, version, created_at, updated_at) "
            "VALUES (:id, :name, 'firecrawl', '{}', 'low', 'approved', 1, :ts, :ts)"
        ),
        {"id": recipe_id, "name": name, "ts": now},
    )
    return recipe_id


class TestUpsertCrawlTarget:
    """Tests for canonical target upsert behavior."""

    def test_creates_target_with_canonical_url_hash(self, db_session):
        """A new target should store normalized URL and canonical hash."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        # Act
        target, created = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="HTTPS://WWW.CHINACDC.CN/path/page.html?utm_source=x&b=2&a=1#frag",
            target_role="detail",
            media_type="html",
        )

        # Assert
        assert created is True
        assert target.source_id == source_id
        assert target.recipe_id == recipe_id
        assert target.canonical_url == "https://www.chinacdc.cn/path/page.html?a=1&b=2"
        assert len(target.canonical_url_hash) == 64
        assert target.status == "pending"

    def test_same_normalized_target_returns_existing_row(self, db_session):
        """Equivalent URLs for the same source and role should not duplicate targets."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        first_seen = datetime(2026, 5, 1, tzinfo=UTC)
        second_seen = first_seen + timedelta(days=1)
        db_session.commit()

        first, created_first = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/path/page.html?b=2&a=1#top",
            target_role="detail",
            media_type="html",
            now=first_seen,
        )

        # Act
        second, created_second = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/path/page.html?a=1&b=2&utm_source=rss",
            target_role="detail",
            media_type="html",
            now=second_seen,
        )
        db_session.flush()

        # Assert
        assert created_first is True
        assert created_second is False
        assert second.id == first.id
        assert second.first_seen_at == first_seen
        assert second.last_seen_at == second_seen
        count = db_session.scalar(sa.select(sa.func.count()).select_from(CrawlTarget))
        assert count == 1

    def test_role_participates_in_idempotency_key(self, db_session):
        """The same URL can exist once per target role."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        # Act
        detail, detail_created = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/path/report.pdf",
            target_role="detail",
            media_type="html",
        )
        asset, asset_created = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/path/report.pdf",
            target_role="asset",
            media_type="pdf",
        )

        # Assert
        assert detail_created is True
        assert asset_created is True
        assert detail.id != asset.id

    def test_find_and_list_targets_by_source(self, db_session):
        """Repository queries should support source, role and status filtering."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        other_source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        target, _ = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/detail.html",
            target_role="detail",
            media_type="html",
        )
        upsert_crawl_target(
            db_session,
            source_id=other_source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/detail.html",
            target_role="detail",
            media_type="html",
        )

        # Act
        found = find_crawl_target(
            db_session,
            source_id=source_id,
            target_role="detail",
            target_url="https://www.chinacdc.cn/detail.html#ignored",
        )
        listed = list_crawl_targets(
            db_session,
            source_id=source_id,
            target_role="detail",
            status="pending",
        )

        # Assert
        assert found is not None
        assert found.id == target.id
        assert [item.id for item in listed] == [target.id]


class TestCreateCrawlJobForTarget:
    """Tests for target crawl job enqueue idempotency."""

    def test_creates_crawl_job_with_stable_idempotency_key(self, db_session):
        """A target crawl job should use a deterministic idempotency key."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()
        target, _ = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/detail.html",
            target_role="detail",
            media_type="html",
            priority=5,
        )

        # Act
        job = create_crawl_job_for_target(db_session, target, auto_commit=False)

        # Assert
        assert job is not None
        assert job.job_type == "crawl"
        assert job.priority == 5
        assert job.payload == {
            "source_id": str(source_id),
            "recipe_id": str(recipe_id),
            "target_id": str(target.id),
        }
        assert job.idempotency_key == (
            f"crawl-target:{target.id}:{target.canonical_url_hash}"
        )

    def test_repeated_enqueue_returns_none(self, db_session):
        """Creating the same target crawl job twice should not duplicate jobs."""
        # Arrange
        source_id = insert_source(db_session, f"source-{uuid.uuid4().hex[:6]}")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()
        target, _ = upsert_crawl_target(
            db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            target_url="https://www.chinacdc.cn/detail.html",
            target_role="detail",
            media_type="html",
        )
        first = create_crawl_job_for_target(db_session, target, auto_commit=False)

        # Act
        second = create_crawl_job_for_target(db_session, target, auto_commit=False)

        # Assert
        assert first is not None
        assert second is None
        count = db_session.scalar(
            sa.text("SELECT count(*) FROM jobs WHERE job_type = 'crawl'")
        )
        assert count == 1
