"""Integration test — Sina feed dedup soak.

Loads sina-feed.json fixture multiple times and verifies that the extraction
pipeline does not produce duplicate content items.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from harvester.db.models import ContentItem, RawObject, Source
from harvester.extractors.sina_fixture import SinaFixtureExtractor
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)

FIXTURES_RAW_DIR = Path(__file__).parent.parent / "fixtures" / "raw"
SINA_FEED_PATH = FIXTURES_RAW_DIR / "sina-feed.json"

# Number of simulated crawl iterations
NUM_ITERATIONS = 5


@pytest.fixture
def sina_feed_payload() -> str:
    """Load the sina-feed.json fixture content."""
    return SINA_FEED_PATH.read_text(encoding="utf-8")


@pytest.fixture
def source_id(db_session) -> uuid.UUID:
    """Create a test source in the database and return its ID."""
    source = Source(
        id=uuid.uuid4(),
        name=f"sina-soak-test-{uuid.uuid4().hex[:8]}",
        kind="sina_weibo",
        url="https://weibo.com/test",
        status="active",
    )
    db_session.add(source)
    db_session.flush()
    return source.id


class TestSinaCompressedSoak:
    """Run extraction pipeline multiple times and verify no duplicates."""

    def test_no_duplicate_content_items_after_multiple_extractions(
        self, db_session, source_id, sina_feed_payload
    ):
        """Extracting the same feed multiple times should not create duplicates.

        Simulates NUM_ITERATIONS crawl runs of the same feed content,
        running the full upsert-observe-version pipeline each time.
        After all iterations, the number of ContentItem rows should match
        the number of distinct items in the fixture (not NUM_ITERATIONS * items).
        """
        extractor = SinaFixtureExtractor()

        # First extraction to determine expected item count
        items = extractor.extract({}, sina_feed_payload)
        expected_count = len(items)
        assert expected_count >= 1, "Feed should contain at least one status"

        for _ in range(NUM_ITERATIONS):
            # Create a raw object for this crawl iteration
            raw = RawObject(
                id=uuid.uuid4(),
                source_id=source_id,
                content_type="application/json",
                content_hash=uuid.uuid4().hex,
            )
            db_session.add(raw)
            db_session.flush()

            # Extract and upsert each candidate item
            candidates = extractor.extract({}, sina_feed_payload)
            for candidate in candidates:
                content_item, created = upsert_content_item(
                    db_session,
                    source_id=source_id,
                    external_item_id=candidate.external_item_id,
                    item_type=candidate.item_type,
                    original_url=candidate.original_url,
                    final_url=candidate.final_url,
                    canonical_url=candidate.canonical_url,
                    canonical_url_hash=candidate.canonical_url_hash,
                    title=candidate.title,
                )

                # Record observation for every extraction
                create_observation(
                    db_session,
                    content_item_id=content_item.id,
                    raw_object_id=raw.id,
                    position=candidate.position,
                    snippet=candidate.snippet,
                )

                # Create version if content changed
                content_hash = str(hash(candidate.content_text))
                create_version_if_changed(
                    db_session,
                    content_item_id=content_item.id,
                    content_hash=content_hash,
                    normalized_text=candidate.content_text,
                    raw_object_id=raw.id,
                )

        # Flush all pending changes before querying
        db_session.flush()

        # Verify: content item count should match unique items, not total extractions
        total_items = db_session.scalar(
            sa.select(sa.func.count()).select_from(ContentItem).where(
                ContentItem.source_id == source_id
            )
        )
        assert total_items == expected_count, (
            f"Expected {expected_count} unique items, got {total_items}. "
            f"Deduplication failed after {NUM_ITERATIONS} iterations."
        )

    def test_observations_created_for_every_extraction(
        self, db_session, source_id, sina_feed_payload
    ):
        """Each extraction run should create an observation per item."""
        from harvester.db.models import ItemObservation

        extractor = SinaFixtureExtractor()
        items = extractor.extract({}, sina_feed_payload)
        expected_items = len(items)

        for _ in range(NUM_ITERATIONS):
            raw = RawObject(
                id=uuid.uuid4(),
                source_id=source_id,
                content_type="application/json",
                content_hash=uuid.uuid4().hex,
            )
            db_session.add(raw)
            db_session.flush()

            candidates = extractor.extract({}, sina_feed_payload)
            for candidate in candidates:
                content_item, _ = upsert_content_item(
                    db_session,
                    source_id=source_id,
                    external_item_id=candidate.external_item_id,
                    item_type=candidate.item_type,
                    title=candidate.title,
                )
                create_observation(
                    db_session,
                    content_item_id=content_item.id,
                    raw_object_id=raw.id,
                    position=candidate.position,
                    snippet=candidate.snippet,
                )

        db_session.flush()

        # Count observations for items belonging to this source
        total_observations = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemObservation)
            .join(ContentItem, ItemObservation.content_item_id == ContentItem.id)
            .where(ContentItem.source_id == source_id)
        )
        assert total_observations == expected_items * NUM_ITERATIONS, (
            f"Expected {expected_items * NUM_ITERATIONS} observations, "
            f"got {total_observations}."
        )
