"""Integration test — Sina 7x24 flash news extraction pipeline.

Uses adapter fake to simulate 7x24 crawl, verifies extractor output flows
through pipeline into content_item and item_version.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from harvester.db.models import ContentItem, ItemVersion, RawObject, Source
from harvester.extractors.sina_7x24 import Sina7x24Extractor
from harvester.jobs.pipeline import (
    create_observation,
    create_version_if_changed,
    upsert_content_item,
)

FIXTURES_RAW_DIR = Path(__file__).parent.parent / "fixtures" / "raw"
FIXTURES_EXPECTED_DIR = Path(__file__).parent.parent / "fixtures" / "expected"
SINA_7X24_RAW_PATH = FIXTURES_RAW_DIR / "sina-7x24.md"
SINA_7X24_EXPECTED_PATH = FIXTURES_EXPECTED_DIR / "sina-7x24-items.json"


@pytest.fixture
def sina_7x24_payload() -> str:
    return SINA_7X24_RAW_PATH.read_text(encoding="utf-8")


@pytest.fixture
def expected_items() -> list[dict]:
    return json.loads(SINA_7X24_EXPECTED_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def source_id(db_session) -> uuid.UUID:
    source = Source(
        id=uuid.uuid4(),
        name=f"sina-7x24-test-{uuid.uuid4().hex[:8]}",
        kind="sina_7x24",
        url="https://finance.sina.com.cn/7x24/",
        status="active",
    )
    db_session.add(source)
    db_session.flush()
    return source.id


class TestSina7x24Pipeline:
    """Verify extractor output passes through content_item/item_version pipeline."""

    def test_creates_content_items_matching_extractor_output(
        self, db_session, source_id, sina_7x24_payload, expected_items
    ):
        extractor = Sina7x24Extractor()
        candidates = extractor.extract({}, sina_7x24_payload)
        assert len(candidates) == len(expected_items)

        raw = RawObject(
            id=uuid.uuid4(),
            source_id=source_id,
            content_type="text/markdown",
            content_hash=uuid.uuid4().hex,
        )
        db_session.add(raw)
        db_session.flush()

        expected_ids = {item["external_item_id"] for item in expected_items}
        for candidate in candidates:
            assert candidate.external_item_id in expected_ids
            content_item, created = upsert_content_item(
                db_session,
                source_id=source_id,
                external_item_id=candidate.external_item_id,
                item_type=candidate.item_type,
                original_url=candidate.original_url,
                final_url=candidate.final_url,
                title=candidate.title,
            )
            assert created
            create_observation(
                db_session,
                content_item_id=content_item.id,
                raw_object_id=raw.id,
                position=candidate.position,
            )
            content_hash = str(hash(candidate.content_text))
            version, version_created = create_version_if_changed(
                db_session,
                content_item_id=content_item.id,
                content_hash=content_hash,
                normalized_text=candidate.content_text,
                raw_object_id=raw.id,
            )
            assert version_created

        db_session.flush()
        total_items = db_session.scalar(
            sa.select(sa.func.count()).select_from(ContentItem).where(
                ContentItem.source_id == source_id
            )
        )
        assert total_items == len(expected_items)

    def test_creates_item_versions(
        self, db_session, source_id, sina_7x24_payload
    ):
        extractor = Sina7x24Extractor()
        candidates = extractor.extract({}, sina_7x24_payload)

        raw = RawObject(
            id=uuid.uuid4(),
            source_id=source_id,
            content_type="text/markdown",
            content_hash=uuid.uuid4().hex,
        )
        db_session.add(raw)
        db_session.flush()

        for candidate in candidates:
            content_item, _ = upsert_content_item(
                db_session,
                source_id=source_id,
                external_item_id=candidate.external_item_id,
                item_type=candidate.item_type,
                title=candidate.title,
            )
            content_hash = str(hash(candidate.content_text))
            create_version_if_changed(
                db_session,
                content_item_id=content_item.id,
                content_hash=content_hash,
                normalized_text=candidate.content_text,
                raw_object_id=raw.id,
            )

        db_session.flush()
        total_versions = db_session.scalar(
            sa.select(sa.func.count())
            .select_from(ItemVersion)
            .join(ContentItem, ItemVersion.content_item_id == ContentItem.id)
            .where(ContentItem.source_id == source_id)
        )
        assert total_versions == len(candidates)

    def test_no_duplicate_items_on_re_extraction(
        self, db_session, source_id, sina_7x24_payload
    ):
        extractor = Sina7x24Extractor()
        candidates = extractor.extract({}, sina_7x24_payload)
        expected_count = len(candidates)

        for _ in range(3):
            raw = RawObject(
                id=uuid.uuid4(),
                source_id=source_id,
                content_type="text/markdown",
                content_hash=uuid.uuid4().hex,
            )
            db_session.add(raw)
            db_session.flush()

            for candidate in extractor.extract({}, sina_7x24_payload):
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
                )

        db_session.flush()
        total_items = db_session.scalar(
            sa.select(sa.func.count()).select_from(ContentItem).where(
                ContentItem.source_id == source_id
            )
        )
        assert total_items == expected_count
