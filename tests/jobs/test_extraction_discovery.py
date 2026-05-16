"""Tests for extraction service target discovery integration."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import sqlalchemy as sa

from harvester.db.models import (
    ContentItem,
    CrawlRun,
    CrawlTarget,
    Job,
    RawObject,
    Recipe,
    Source,
)
from harvester.domain.urls import compute_canonical_url_hash, normalize_url
from harvester.extractors.base import CandidateItem, DiscoveredTarget, ExtractionOutput
from harvester.jobs.extraction import execute_extraction


class _DiscoveryExtractor:
    def extract(self, raw_metadata: dict, raw_payload: str | bytes):
        return ExtractionOutput(
            items=[
                CandidateItem(
                    external_item_id="cncdc-flu-weekly:2026:18",
                    item_type="article",
                    title="中国流感监测周报",
                    canonical_url="https://www.chinacdc.cn/detail.html",
                    canonical_url_hash=compute_canonical_url_hash(
                        "https://www.chinacdc.cn/detail.html"
                    ),
                    content_text="weekly flu report summary",
                    language="zh",
                    observed_url=raw_metadata["source_url"],
                )
            ],
            discovered_targets=[
                DiscoveredTarget(
                    target_url=(
                        "https://www.chinacdc.cn/jksj/jksj04_14249/202605/"
                        "t20260514_1835783.html"
                    ),
                    target_role="detail",
                    media_type="html",
                    content_type="text/html",
                    external_item_id="cncdc-flu-weekly:2026:18",
                    depth=1,
                    priority=10,
                )
            ],
        )


def _seed_extraction_context(db_session, tmp_path):
    source = Source(
        id=uuid.uuid4(),
        name=f"cdc-{uuid.uuid4().hex[:6]}",
        kind="web",
        url="https://www.chinacdc.cn/jksj/jksj04_14249/",
        status="watched",
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    recipe = Recipe(
        id=uuid.uuid4(),
        name=f"cdc-recipe-{uuid.uuid4().hex[:6]}",
        executor="firecrawl",
        config={
            "discovery": {
                "enabled": True,
                "max_depth": 2,
                "max_targets_per_run": 5,
                "allowed_hosts": ["www.chinacdc.cn"],
                "allowed_path_prefixes": ["/jksj/jksj04_14249/"],
                "allowed_content_types": ["text/html", "application/pdf"],
            }
        },
        risk_level="low",
        approval_status="approved",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    payload_path = tmp_path / "cdc-list.html"
    payload_path.write_text("<html>cdc list</html>", encoding="utf-8")
    raw = RawObject(
        id=uuid.uuid4(),
        source_id=source.id,
        content_type="text/html",
        content_hash="sha256:list",
        storage_uri=f"file://{payload_path}",
        byte_size=payload_path.stat().st_size,
        retention_policy="raw",
        compressed=False,
        created_at=datetime.now(UTC),
    )
    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        recipe_id=recipe.id,
        status="completed",
        raw_object_id=raw.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add_all([source, recipe])
    db_session.flush()
    db_session.add(raw)
    db_session.flush()
    db_session.add(run)
    db_session.commit()
    return source, recipe, raw


def _add_raw_object_for_recipe(db_session, tmp_path, source: Source, recipe: Recipe):
    payload_path = tmp_path / f"cdc-list-{uuid.uuid4().hex[:6]}.html"
    payload_path.write_text("<html>cdc list changed</html>", encoding="utf-8")
    raw = RawObject(
        id=uuid.uuid4(),
        source_id=source.id,
        content_type="text/html",
        content_hash=f"sha256:{uuid.uuid4().hex}",
        storage_uri=f"file://{payload_path}",
        byte_size=payload_path.stat().st_size,
        retention_policy="raw",
        compressed=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(raw)
    db_session.flush()
    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        recipe_id=recipe.id,
        status="completed",
        raw_object_id=raw.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.commit()
    return raw


class TestExtractionDiscoveryIntegration:
    """Tests for discovered targets created during extraction."""

    def test_extraction_upserts_target_and_creates_crawl_job(
        self, db_session, tmp_path
    ):
        """Extraction should persist in-scope targets and enqueue target crawl jobs."""
        # Arrange
        source, recipe, raw = _seed_extraction_context(db_session, tmp_path)

        # Act
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_DiscoveryExtractor(),
        ):
            result = execute_extraction(
                db_session,
                raw_object_id=raw.id,
                actor="test",
            )

        # Assert
        assert result.items_extracted == 1
        assert result.versions_created == 1
        target = db_session.scalar(sa.select(CrawlTarget))
        assert target is not None
        assert target.source_id == source.id
        assert target.recipe_id == recipe.id
        assert target.target_role == "detail"
        assert target.media_type == "html"
        assert target.depth == 1
        assert target.priority == 10
        assert target.discovered_from_raw_object_id == raw.id
        assert target.external_item_id == "cncdc-flu-weekly:2026:18"
        assert target.canonical_url == normalize_url(target.target_url)

        job = db_session.scalar(sa.select(Job).where(Job.job_type == "crawl"))
        assert job is not None
        assert job.payload["target_id"] == str(target.id)
        assert job.idempotency_key == (
            f"crawl-target:{target.id}:{target.canonical_url_hash}"
        )

    def test_out_of_scope_target_is_skipped_with_audit(self, db_session, tmp_path):
        """Out-of-scope discovered targets should not create targets or jobs."""
        # Arrange
        _, _, raw = _seed_extraction_context(db_session, tmp_path)

        class OutOfScopeExtractor:
            def extract(self, raw_metadata: dict, raw_payload: str | bytes):
                return ExtractionOutput(
                    discovered_targets=[
                        DiscoveredTarget(
                            target_url="https://evil.example/detail.html",
                            target_role="detail",
                            media_type="html",
                            content_type="text/html",
                            depth=1,
                        )
                    ]
                )

        # Act
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=OutOfScopeExtractor(),
        ):
            execute_extraction(db_session, raw_object_id=raw.id, actor="test")

        # Assert
        assert (
            db_session.scalar(sa.select(sa.func.count()).select_from(CrawlTarget)) == 0
        )
        assert db_session.scalar(sa.select(sa.func.count()).select_from(Job)) == 0
        reason = db_session.scalar(
            sa.text(
                "SELECT reason FROM audit_events WHERE action = 'crawl_target_skipped'"
            )
        )
        assert reason == "host_not_allowed"

    def test_repeated_list_observation_does_not_duplicate_target_or_job(
        self, db_session, tmp_path
    ):
        """Rewind re-observation should update existing target without duplicate jobs."""
        # Arrange
        _, _, raw = _seed_extraction_context(db_session, tmp_path)

        # Act
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_DiscoveryExtractor(),
        ):
            execute_extraction(db_session, raw_object_id=raw.id, actor="test")
            execute_extraction(db_session, raw_object_id=raw.id, actor="test")

        # Assert
        target_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(CrawlTarget)
        )
        job_count = db_session.scalar(sa.select(sa.func.count()).select_from(Job))
        item_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(ContentItem)
        )
        assert target_count == 1
        crawl_job_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(Job).where(Job.job_type == "crawl")
        )
        assert crawl_job_count == 1
        assert item_count == 1

    def test_changed_url_with_stable_external_item_id_reuses_content_item(
        self, db_session, tmp_path
    ):
        """A URL change should not duplicate content when external item ID is stable."""
        # Arrange
        source, recipe, raw1 = _seed_extraction_context(db_session, tmp_path)
        raw2 = _add_raw_object_for_recipe(db_session, tmp_path, source, recipe)

        class ChangedUrlExtractor(_DiscoveryExtractor):
            def extract(self, raw_metadata: dict, raw_payload: str | bytes):
                output = super().extract(raw_metadata, raw_payload)
                output.items[0].canonical_url = "https://www.chinacdc.cn/changed.html"
                output.items[0].canonical_url_hash = compute_canonical_url_hash(
                    output.items[0].canonical_url
                )
                output.discovered_targets[0].target_url = (
                    "https://www.chinacdc.cn/jksj/jksj04_14249/202605/"
                    "t20260515_changed.html"
                )
                return output

        # Act
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_DiscoveryExtractor(),
        ):
            execute_extraction(db_session, raw_object_id=raw1.id, actor="test")
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=ChangedUrlExtractor(),
        ):
            execute_extraction(db_session, raw_object_id=raw2.id, actor="test")

        # Assert
        item_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(ContentItem)
        )
        target_count = db_session.scalar(
            sa.select(sa.func.count()).select_from(CrawlTarget)
        )
        assert item_count == 1
        assert target_count == 2
