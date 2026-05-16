"""End-to-end test for CDC weekly list -> detail -> PDF pipeline.

Uses deterministic fixtures — no network access.
"""

import json
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from fpdf import FPDF

from harvester.db.models import (
    Chunk,
    ContentItem,
    CrawlRun,
    CrawlTarget,
    ItemVersion,
    Job,
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

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"
SOURCE_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"
DETAIL_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/t20260514_1835783.html"
PDF_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/202605/P020260514670474006354.pdf"
EXTERNAL_ITEM_ID = "cncdc-flu-weekly:2026:W18:issue-908"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / "raw" / name).read_text(encoding="utf-8")


def _make_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "CDC weekly flu report content", new_x="LMARGIN", new_y="NEXT")
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


class TestCdcWeeklyE2EPipeline:
    """Full pipeline: list -> detail -> PDF -> content item -> version -> chunk -> embedding job."""

    def test_full_pipeline(self, db_session, tmp_path):
        source, recipe = _seed(db_session, tmp_path)

        # Stage 1: List page extraction
        list_html = _read_fixture("cdc-weekly-list.html")
        raw_list = _add_raw(
            db_session, tmp_path, source, recipe, list_html, "text/html"
        )

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=CdcWeeklyListExtractor(),
        ):
            result_list = execute_extraction(
                db_session, raw_object_id=raw_list.id, actor="test"
            )

        assert result_list.items_extracted >= 1
        assert result_list.versions_created >= 1

        # Verify detail targets were discovered
        targets = db_session.scalars(
            sa.select(CrawlTarget).where(CrawlTarget.target_role == "detail")
        ).all()
        assert len(targets) >= 1

        # Verify crawl jobs were created for targets
        crawl_jobs = db_session.scalars(
            sa.select(Job).where(Job.job_type == "crawl")
        ).all()
        assert len(crawl_jobs) >= 1

        # Stage 2: Detail page extraction
        detail_html = _read_fixture("cdc-weekly-detail.html")
        raw_detail = _add_raw(
            db_session, tmp_path, source, recipe, detail_html, "text/html"
        )

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=CdcWeeklyDetailExtractor(),
        ):
            result_detail = execute_extraction(
                db_session, raw_object_id=raw_detail.id, actor="test"
            )

        assert result_detail.items_extracted == 1

        # Verify PDF asset target was discovered
        pdf_targets = db_session.scalars(
            sa.select(CrawlTarget).where(CrawlTarget.target_role == "asset")
        ).all()
        assert len(pdf_targets) >= 1
        assert pdf_targets[0].media_type == "pdf"

        # Stage 3: PDF extraction
        pdf_bytes = _make_pdf_bytes()
        raw_pdf = _add_raw(
            db_session,
            tmp_path,
            source,
            recipe,
            pdf_bytes,
            "application/pdf",
        )

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=PdfTextExtractor(),
        ):
            result_pdf = execute_extraction(
                db_session, raw_object_id=raw_pdf.id, actor="test"
            )

        assert result_pdf.items_extracted == 1
        assert result_pdf.versions_created == 1

        # Verify content item has correct external_item_id
        item = db_session.scalar(
            sa.select(ContentItem).where(
                ContentItem.external_item_id == EXTERNAL_ITEM_ID
            )
        )
        assert item is not None

        # Verify item versions exist (list + detail + PDF)
        versions = db_session.scalars(
            sa.select(ItemVersion)
            .where(ItemVersion.content_item_id == item.id)
            .order_by(ItemVersion.created_at)
        ).all()
        assert len(versions) >= 2  # at least detail + PDF

        # Verify chunks were created
        chunks = db_session.scalars(
            sa.select(Chunk)
            .join(ItemVersion, ItemVersion.id == Chunk.item_version_id)
            .where(ItemVersion.content_item_id == item.id)
        ).all()
        assert len(chunks) > 0

        # Verify embedding jobs were created
        embed_jobs = db_session.scalars(
            sa.select(Job).where(Job.job_type == "embed_chunks")
        ).all()
        assert len(embed_jobs) >= 1
