"""Tests for target traceability — search results traceable back to PDF raw object,
detail target, list observation, and Source."""

import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from fpdf import FPDF

from harvester.db.models import (
    ContentItem,
    CrawlRun,
    CrawlTarget,
    ItemObservation,
    ItemVersion,
    RawObject,
    Recipe,
    Source,
)
from harvester.domain.urls import compute_canonical_url_hash
from harvester.extractors.cdc_weekly import (
    CdcWeeklyDetailExtractor,
    CdcWeeklyListExtractor,
)
from harvester.extractors.pdf_text import PdfTextExtractor
from harvester.jobs.extraction import execute_extraction

SOURCE_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"
DETAIL_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"
PDF_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/P020260514670474006354.pdf"

LIST_HTML = """\
<!DOCTYPE html><html><body>
<ul class="xwzx_list">
  <li><a href="./202605/t20260514_1835783.html">中国流感监测周报（2026年第18周 第908期）</a>
    <span class="date">2026-05-14</span></li>
</ul></body></html>"""

DETAIL_HTML = """\
<!DOCTYPE html><html><body>
<div class="content">
  <h1>中国流感监测周报（2026年第18周 第908期）</h1>
  <p>正文摘要。</p>
  <p><a href="./P020260514670474006354.pdf">PDF下载</a></p>
</div></body></html>"""


def _make_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Full PDF report text", new_x="LMARGIN", new_y="NEXT")
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _seed(db_session, tmp_path):
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
        config={
            "discovery": {
                "enabled": True,
                "max_depth": 2,
                "max_targets_per_run": 20,
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
    db_session.add_all([source, recipe])
    db_session.commit()
    return source, recipe


def _add_raw(db_session, tmp_path, source, recipe, content, content_type):
    path = tmp_path / f"raw-{uuid.uuid4().hex[:6]}.raw"
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
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


def _run_pipeline(db_session, tmp_path, source, recipe):
    """Run all three stages and return raw objects."""

    # Stage 1: List page extraction — discovers detail targets
    raw_list = _add_raw(db_session, tmp_path, source, recipe, LIST_HTML, "text/html")
    with patch(
        "harvester.jobs.extraction.get_extractor",
        return_value=CdcWeeklyListExtractor(),
    ):
        execute_extraction(db_session, raw_object_id=raw_list.id, actor="test")

    # Stage 2: Detail page extraction
    raw_detail = _add_raw(
        db_session, tmp_path, source, recipe, DETAIL_HTML, "text/html"
    )
    # Link the raw object to the detail target (created by list extraction)
    detail_target = db_session.scalar(
        sa.select(CrawlTarget).where(CrawlTarget.target_role == "detail")
    )
    detail_target.last_raw_object_id = raw_detail.id
    detail_target.status = "completed"
    db_session.commit()

    with patch(
        "harvester.jobs.extraction.get_extractor",
        return_value=CdcWeeklyDetailExtractor(),
    ):
        execute_extraction(db_session, raw_object_id=raw_detail.id, actor="test")

    # Stage 3: PDF extraction
    raw_pdf = _add_raw(
        db_session, tmp_path, source, recipe, _make_pdf_bytes(), "application/pdf"
    )
    # Link the raw object to the PDF asset target
    pdf_target = db_session.scalar(
        sa.select(CrawlTarget).where(CrawlTarget.target_role == "asset")
    )
    pdf_target.last_raw_object_id = raw_pdf.id
    pdf_target.status = "completed"
    db_session.commit()

    with patch(
        "harvester.jobs.extraction.get_extractor",
        return_value=PdfTextExtractor(),
    ):
        execute_extraction(db_session, raw_object_id=raw_pdf.id, actor="test")

    return raw_list, raw_detail, raw_pdf


class TestTargetTraceability:
    """Verify traceability from content item back to raw objects, targets, and source."""

    def test_content_item_traces_to_source(self, db_session, tmp_path):
        """Content item should be linked to the original Source."""
        source, recipe = _seed(db_session, tmp_path)
        raw_list, raw_detail, raw_pdf = _run_pipeline(
            db_session, tmp_path, source, recipe
        )

        item = db_session.scalar(sa.select(ContentItem))
        assert item.source_id == source.id

    def test_version_traces_to_pdf_raw_object(self, db_session, tmp_path):
        """PDF item version should reference the PDF raw object."""
        source, recipe = _seed(db_session, tmp_path)
        raw_list, raw_detail, raw_pdf = _run_pipeline(
            db_session, tmp_path, source, recipe
        )

        # Find the PDF version (latest)
        item = db_session.scalar(sa.select(ContentItem))
        versions = db_session.scalars(
            sa.select(ItemVersion)
            .where(ItemVersion.content_item_id == item.id)
            .order_by(ItemVersion.created_at.desc())
        ).all()
        pdf_version = versions[0]
        assert pdf_version.raw_object_id == raw_pdf.id

        # Raw object is a PDF
        raw = db_session.get(RawObject, pdf_version.raw_object_id)
        assert raw.content_type == "application/pdf"

    def test_detail_target_exists_and_links_to_source(self, db_session, tmp_path):
        """Detail crawl target should be linked to the source."""
        source, recipe = _seed(db_session, tmp_path)
        _run_pipeline(db_session, tmp_path, source, recipe)

        detail_target = db_session.scalar(
            sa.select(CrawlTarget).where(CrawlTarget.target_role == "detail")
        )
        assert detail_target is not None
        assert detail_target.source_id == source.id
        assert DETAIL_URL in detail_target.target_url

    def test_pdf_asset_target_exists(self, db_session, tmp_path):
        """PDF asset target should exist with correct role and media type."""
        source, recipe = _seed(db_session, tmp_path)
        _run_pipeline(db_session, tmp_path, source, recipe)

        pdf_target = db_session.scalar(
            sa.select(CrawlTarget).where(CrawlTarget.target_role == "asset")
        )
        assert pdf_target is not None
        assert pdf_target.media_type == "pdf"
        assert PDF_URL in pdf_target.target_url

    def test_list_observation_exists(self, db_session, tmp_path):
        """Content item should have an observation from the list page."""
        source, recipe = _seed(db_session, tmp_path)
        raw_list, _, _ = _run_pipeline(db_session, tmp_path, source, recipe)

        item = db_session.scalar(sa.select(ContentItem))
        obs = db_session.scalar(
            sa.select(ItemObservation).where(
                ItemObservation.content_item_id == item.id,
                ItemObservation.raw_object_id == raw_list.id,
            )
        )
        assert obs is not None
        assert obs.observed_url == SOURCE_URL
