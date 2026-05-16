"""Sina 7x24 live crawl smoke test.

Opt-in test that only runs when HARVESTER_ENABLE_LIVE_CRAWL=1.
Crawls the real Sina 7x24 page, extracts flash news, and validates
the full pipeline: crawl -> extract -> content_item -> observation -> version.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

from harvester.adapters.firecrawl import FirecrawlAdapter
from harvester.db.models import ContentItem, ItemVersion, RawObject, Source
from harvester.extractors.sina_7x24 import Sina7x24Extractor
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)

LIVE_CRAWL_ENABLED = os.environ.get("HARVESTER_ENABLE_LIVE_CRAWL", "").strip() == "1"

SINA_7X24_URL = "https://finance.sina.com.cn/7x24/"


def _insert_source(db_session) -> Source:
    """Insert a test Source for Sina 7x24 and return the ORM instance."""
    source = Source(
        id=uuid.uuid4(),
        name=f"sina-7x24-live-{uuid.uuid4().hex[:8]}",
        kind="web",
        url=SINA_7X24_URL,
        status="watched",
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(source)
    db_session.flush()
    return source


@pytest.mark.skipif(not LIVE_CRAWL_ENABLED, reason="HARVESTER_ENABLE_LIVE_CRAWL not set")
class TestSina7x24LiveCrawlSmoke:
    """Live smoke test — only runs when HARVESTER_ENABLE_LIVE_CRAWL=1.

    Crawls the real Sina 7x24 page via FirecrawlAdapter, extracts flash news
    items with Sina7x24Extractor, and validates the full pipeline produces
    content_items, observations, and item_versions in the database.
    """

    def test_live_sina_7x24_crawl(self, db_session):
        """Execute a real crawl against Sina 7x24 and verify end-to-end."""
        # 1. Create a Source ORM object
        source = _insert_source(db_session)

        # 2. Fetch real page via FirecrawlAdapter
        adapter = FirecrawlAdapter.from_env()
        result = adapter.crawl(SINA_7X24_URL)

        # 3. Assert crawl result has payload_text
        assert result.payload_text is not None, (
            f"Crawl returned no payload_text. Error: {result.error}"
        )
        html = result.payload_text

        # 4. Create a RawObject ORM object
        content_hash = hashlib.sha256(html.encode()).hexdigest()
        raw_obj = RawObject(
            source_id=source.id,
            content_type="text/html",
            storage_uri="live://sina-7x24",
            content_hash=content_hash,
            byte_size=len(html.encode()),
        )
        db_session.add(raw_obj)
        db_session.flush()

        # 5. Run Sina7x24Extractor to get candidates
        extractor = Sina7x24Extractor()
        candidates = extractor.extract({}, html)

        # 6. Assert candidates were extracted
        assert len(candidates) > 0, "Extractor produced no candidates from live page"

        # 7. For each candidate, run pipeline: upsert -> observe -> version
        for c in candidates:
            item, created = upsert_content_item(
                db_session,
                source_id=source.id,
                item_type=c.item_type,
                external_item_id=c.external_item_id,
                original_url=c.original_url,
                final_url=c.final_url,
                title=c.title,
            )
            create_observation(
                db_session,
                content_item_id=item.id,
                raw_object_id=raw_obj.id,
            )
            hash_str = hashlib.sha256(
                (c.content_text or "").encode()
            ).hexdigest()
            create_version_if_changed(
                db_session,
                content_item_id=item.id,
                content_hash=hash_str,
                normalized_text=c.content_text,
                language=c.language,
            )

        db_session.flush()

        # 8. Assert content_items exist in DB
        item_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentItem)
            .where(ContentItem.source_id == source.id)
        )
        assert item_count > 0, "No content_items found in database"

        # 9. Assert item_versions exist in DB
        version_count = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemVersion)
            .join(ContentItem, ItemVersion.content_item_id == ContentItem.id)
            .where(ContentItem.source_id == source.id)
        )
        assert version_count > 0, "No item_versions found in database"
