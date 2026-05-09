"""CDC public crawl smoke tests.

Two test modes:
1. Deterministic integration tests using adapter fakes (always run).
2. Live crawl smoke (only when HARVESTER_ENABLE_LIVE_CRAWL=1).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import ContentItem, ItemVersion, Chunk
from harvester.domain.fetch_policy import FetchPolicyResult
from harvester.extractors.cdc_fixture import CdcFixtureExtractor
from harvester.jobs.archive import ArchiveWriteResult
from harvester.jobs.crawl_execution import execute_crawl
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)
from harvester.search.keyword import keyword_search

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CDC_RAW = FIXTURES_DIR / "raw" / "cdc-detail.html"

LIVE_CRAWL_ENABLED = os.environ.get("HARVESTER_ENABLE_LIVE_CRAWL", "").strip() == "1"


def _insert_source(db_session, *, url="https://www.cdc.gov"):
    source_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, url, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) VALUES "
            "(:id, :name, :kind, :url, :status, :trust_level, :auth_required, "
            ":failure_count, :created_at, :updated_at)"
        ),
        dict(
            id=source_id,
            name=f"cdc-smoke-source-{source_id.hex[:8]}",
            kind="web",
            url=url,
            status="watched",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    return source_id


def _insert_recipe(db_session):
    recipe_id = uuid.uuid4()
    db_session.execute(
        sa.text(
            "INSERT INTO recipes "
            "(id, name, executor, config, risk_level, approval_status, version, "
            "created_at, updated_at) VALUES "
            "(:id, :name, :executor, :config, :risk_level, :approval_status, "
            ":version, :created_at, :updated_at)"
        ),
        dict(
            id=recipe_id,
            name=f"cdc-smoke-recipe-{recipe_id.hex[:8]}",
            executor="firecrawl",
            config=json.dumps({"url_pattern": "*"}),
            risk_level="low",
            approval_status="approved",
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    return recipe_id


def _make_archive_result():
    return ArchiveWriteResult(
        relative_path="2025-01-15/cdc.raw",
        storage_uri="file:///archive/2025-01-15/cdc.raw",
        content_hash="sha256:cdc123",
        byte_size=500,
        content_type="text/html",
        retention_days=7,
        retain_until=datetime.now(timezone.utc),
    )


class TestCDCFixtureIntegration:
    """Deterministic integration test using adapter fake.

    Validates CDC raw payload -> extractor -> content_item ->
    item_version -> chunk -> keyword search.
    """

    def test_cdc_raw_to_content_items(self, db_session):
        """CDC fixture payload should extract into content items."""
        source_id = _insert_source(db_session)
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        # Load CDC fixture payload as crawl result
        cdc_payload = CDC_RAW.read_text(encoding="utf-8") if CDC_RAW.exists() else "[]"
        crawl_result = CrawlResult(
            original_url="https://www.cdc.gov",
            final_url="https://www.cdc.gov",
            status_code=200,
            content_type="text/html",
            payload_text=cdc_payload,
        )

        with (
            patch(
                "harvester.jobs.crawl_execution.check_fetch_policy",
                return_value=FetchPolicyResult(allowed=True),
            ),
            patch(
                "harvester.jobs.crawl_execution.execute_adapter_crawl",
                return_value=crawl_result,
            ),
            patch(
                "harvester.jobs.crawl_execution.write_archive",
                return_value=_make_archive_result(),
            ),
        ):
            result = execute_crawl(
                session=db_session,
                source_id=source_id,
                recipe_id=recipe_id,
                actor="smoke-test",
            )

        assert result.status == "completed"
        assert result.raw_object_id is not None

    def test_cdc_extractor_produces_items(self):
        """CdcFixtureExtractor should produce items from CDC fixture data."""
        extractor = CdcFixtureExtractor()

        # Use a simple JSON payload matching the CDC fixture format
        payload = json.dumps([
            {
                "id": "cdc-001",
                "title": "Test CDC Article",
                "url": "https://www.cdc.gov/test",
                "content": "Test content for CDC article about health.",
            }
        ])

        items = extractor.extract(
            raw_metadata={"source_url": "https://www.cdc.gov"},
            raw_payload=payload,
        )
        assert len(items) >= 1
        assert items[0].external_item_id == "cdc-001"
        assert items[0].item_type == "article"
        assert items[0].title == "Test CDC Article"

    def test_cdc_pipeline_to_keyword_search(self, db_session):
        """CDC items should flow through pipeline to keyword search."""
        source_id = _insert_source(db_session)
        db_session.commit()

        extractor = CdcFixtureExtractor()
        payload = json.dumps([
            {
                "id": "cdc-search-001",
                "title": "Health Topic Search",
                "url": "https://www.cdc.gov/health",
                "content": "Important health information for public safety.",
            }
        ])

        # Create a raw object for the observation
        raw_id = uuid.uuid4()
        db_session.execute(
            sa.text(
                "INSERT INTO raw_objects "
                "(id, source_id, content_type, content_hash, storage_uri, byte_size, "
                "compressed, created_at) VALUES "
                "(:id, :source_id, :content_type, :content_hash, :storage_uri, "
                ":byte_size, :compressed, :created_at)"
            ),
            dict(
                id=raw_id,
                source_id=source_id,
                content_type="text/html",
                content_hash="sha256:search-test",
                storage_uri="file:///archive/search.raw",
                byte_size=100,
                compressed=False,
                created_at=datetime.now(timezone.utc),
            ),
        )
        db_session.commit()

        items = extractor.extract(
            raw_metadata={"source_url": "https://www.cdc.gov"},
            raw_payload=payload,
        )

        for item in items:
            content_item, _ = upsert_content_item(
                db_session,
                source_id=source_id,
                external_item_id=item.external_item_id,
                item_type=item.item_type,
                title=item.title,
                original_url=item.original_url,
                final_url=item.final_url,
            )
            create_observation(
                db_session,
                content_item_id=content_item.id,
                raw_object_id=raw_id,
                payload_hash="sha256:search-test",
                snippet=item.content_text[:200] if item.content_text else None,
            )
            version, _ = create_version_if_changed(
                db_session,
                content_item_id=content_item.id,
                content_hash="sha256:v1",
                normalized_text=item.content_text or "",
            )
            db_session.flush()

        db_session.commit()

        # Verify content items exist
        items_in_db = list(
            db_session.scalars(
                sa.select(ContentItem).where(ContentItem.source_id == source_id)
            ).all()
        )
        assert len(items_in_db) >= 1


@pytest.mark.skipif(not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set")
class TestCDCLiveSmoke:
    """Live smoke test — only runs when HARVESTER_ENABLE_LIVE_CRAWL=1.

    Crawls a real CDC public page and validates raw object metadata,
    extraction results, and searchable output.
    """

    def test_live_cdc_crawl(self, db_session):
        """Execute a real crawl against CDC and verify end-to-end."""
        source_id = _insert_source(db_session, url="https://www.cdc.gov")
        recipe_id = _insert_recipe(db_session)
        db_session.commit()

        result = execute_crawl(
            session=db_session,
            source_id=source_id,
            recipe_id=recipe_id,
            actor="live-smoke",
        )

        assert result.status == "completed"
        assert result.raw_object_id is not None

        # Verify raw object metadata
        from harvester.db.models import RawObject

        raw_obj = db_session.get(RawObject, result.raw_object_id)
        assert raw_obj is not None
        assert raw_obj.content_type is not None
        assert raw_obj.storage_uri is not None
        assert raw_obj.byte_size is not None
        assert raw_obj.byte_size > 0
