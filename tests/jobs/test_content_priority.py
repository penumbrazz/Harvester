"""Tests for recipe content priority — PDF text over HTML fallback."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import sqlalchemy as sa

from harvester.db.models import (
    ContentItem,
    CrawlRun,
    ItemVersion,
    RawObject,
    Recipe,
    Source,
)
from harvester.extractors.base import CandidateItem, ExtractionOutput
from harvester.jobs.extraction import execute_extraction

DETAIL_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"
PDF_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/P020260514670474006354.pdf"
SOURCE_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"


def _seed(db_session, tmp_path, *, url=None, content_type="text/html"):
    source = Source(
        id=uuid.uuid4(),
        name=f"cdc-{uuid.uuid4().hex[:6]}",
        kind="web",
        url=SOURCE_URL,
        status="watched",
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    recipe = Recipe(
        id=uuid.uuid4(),
        name=f"recipe-{uuid.uuid4().hex[:6]}",
        executor="firecrawl",
        config={},
        risk_level="low",
        approval_status="approved",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    path = tmp_path / f"payload-{uuid.uuid4().hex[:6]}.raw"
    path.write_bytes(b"content")
    raw = RawObject(
        id=uuid.uuid4(),
        source_id=source.id,
        content_type=content_type,
        content_hash=f"sha256:{uuid.uuid4().hex}",
        storage_uri=f"file://{path}",
        byte_size=path.stat().st_size,
        retention_policy="raw",
        compressed=False,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([source, recipe])
    db_session.flush()
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
    return source, recipe, raw


def _add_raw(db_session, source, recipe, tmp_path, *, content_type="text/html"):
    path = tmp_path / f"payload-{uuid.uuid4().hex[:6]}.raw"
    path.write_bytes(b"content")
    raw = RawObject(
        id=uuid.uuid4(),
        source_id=source.id,
        content_type=content_type,
        content_hash=f"sha256:{uuid.uuid4().hex}",
        storage_uri=f"file://{path}",
        byte_size=path.stat().st_size,
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


class TestContentPriority:
    """PDF text should take priority over detail HTML fallback."""

    def test_both_html_and_pdf_versions_coexist(self, db_session, tmp_path):
        """Detail HTML and PDF should both create versions for the same content item."""
        source, recipe, raw_detail = _seed(
            db_session, tmp_path, content_type="text/html"
        )

        # Simulate detail extraction
        detail_extractor = _make_extractor("HTML detail text", "item-001")
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=detail_extractor,
        ):
            execute_extraction(db_session, raw_object_id=raw_detail.id, actor="test")

        # Now simulate PDF extraction for the same content item (same source)
        raw_pdf = _add_raw(
            db_session, source, recipe, tmp_path, content_type="application/pdf"
        )
        pdf_extractor = _make_extractor("PDF extracted text content", "item-001")
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=pdf_extractor,
        ):
            execute_extraction(db_session, raw_object_id=raw_pdf.id, actor="test")

        # Same content item
        items = db_session.scalars(sa.select(ContentItem)).all()
        assert len(items) == 1

        # Two versions: HTML and PDF
        versions = db_session.scalars(
            sa.select(ItemVersion).order_by(ItemVersion.created_at)
        ).all()
        assert len(versions) == 2
        assert versions[0].normalized_text == "HTML detail text"
        assert versions[1].normalized_text == "PDF extracted text content"

    def test_pdf_version_is_latest(self, db_session, tmp_path):
        """PDF version (processed after detail) should be the latest version."""
        source, recipe, raw_detail = _seed(
            db_session, tmp_path, content_type="text/html"
        )

        detail_extractor = _make_extractor("HTML text", "item-001")
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=detail_extractor,
        ):
            execute_extraction(db_session, raw_object_id=raw_detail.id, actor="test")

        raw_pdf = _add_raw(
            db_session, source, recipe, tmp_path, content_type="application/pdf"
        )
        pdf_extractor = _make_extractor("PDF text", "item-001")
        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=pdf_extractor,
        ):
            execute_extraction(db_session, raw_object_id=raw_pdf.id, actor="test")

        item = db_session.scalar(sa.select(ContentItem))
        latest_version = db_session.scalar(
            sa.select(ItemVersion)
            .where(ItemVersion.content_item_id == item.id)
            .order_by(ItemVersion.created_at.desc())
            .limit(1)
        )
        assert latest_version.normalized_text == "PDF text"


def _make_extractor(text: str, external_id: str):
    class _Ext:
        def extract(self, raw_metadata, raw_payload):
            return ExtractionOutput(
                items=[
                    CandidateItem(
                        external_item_id=external_id,
                        item_type="article",
                        title="Test",
                        content_text=text,
                        language="zh",
                        observed_url=raw_metadata.get("source_url"),
                    )
                ]
            )

    return _Ext()
