"""Tests for extraction service creating chunks and embedding jobs."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import sqlalchemy as sa

from harvester.db.models import Chunk, ContentItem, CrawlRun, Job, RawObject, Recipe, Source
from harvester.extractors.base import CandidateItem, ExtractionOutput
from harvester.jobs.extraction import execute_extraction


def _seed(db_session, tmp_path):
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
        name=f"recipe-{uuid.uuid4().hex[:6]}",
        executor="firecrawl",
        config={},
        risk_level="low",
        approval_status="approved",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text("content for extraction", encoding="utf-8")
    raw = RawObject(
        id=uuid.uuid4(),
        source_id=source.id,
        content_type="text/html",
        content_hash="sha256:test",
        storage_uri=f"file://{payload_path}",
        byte_size=payload_path.stat().st_size,
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


class _TextExtractor:
    def extract(self, raw_metadata: dict, raw_payload: str | bytes):
        return ExtractionOutput(
            items=[
                CandidateItem(
                    external_item_id="item-001",
                    item_type="article",
                    title="Test Article",
                    content_text="A " * 600,
                    language="en",
                    observed_url=raw_metadata.get("source_url"),
                )
            ]
        )


class TestExtractionChunking:
    """Extraction should create chunks and embedding jobs for new versions."""

    def test_extraction_creates_chunks_from_normalized_text(
        self, db_session, tmp_path
    ):
        """New item version should be chunked and stored in DB."""
        _, _, raw = _seed(db_session, tmp_path)

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_TextExtractor(),
        ):
            result = execute_extraction(db_session, raw_object_id=raw.id, actor="test")

        assert result.versions_created == 1

        chunks = db_session.scalars(
            sa.select(Chunk).order_by(Chunk.chunk_index)
        ).all()
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text
            assert chunk.embedding_status == "pending"

    def test_extraction_creates_embedding_jobs(self, db_session, tmp_path):
        """Each chunk should get an embedding job."""
        _, _, raw = _seed(db_session, tmp_path)

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_TextExtractor(),
        ):
            result = execute_extraction(db_session, raw_object_id=raw.id, actor="test")

        embed_jobs = db_session.scalars(
            sa.select(Job).where(Job.job_type == "embed_chunks")
        ).all()
        chunks = db_session.scalars(sa.select(Chunk)).all()
        assert len(embed_jobs) == len(chunks)
        for job in embed_jobs:
            assert "chunk_id" in job.payload

    def test_no_chunks_for_unchanged_version(self, db_session, tmp_path):
        """Repeated extraction with same content should not duplicate chunks."""
        source, _, raw = _seed(db_session, tmp_path)

        with patch(
            "harvester.jobs.extraction.get_extractor",
            return_value=_TextExtractor(),
        ):
            execute_extraction(db_session, raw_object_id=raw.id, actor="test")
            execute_extraction(db_session, raw_object_id=raw.id, actor="test")

        chunks = db_session.scalars(sa.select(Chunk)).all()
        assert len(chunks) > 0
        # Chunks should only be created once (content hash is the same)
        from harvester.db.models import ItemVersion
        item = db_session.scalar(sa.select(ContentItem))
        versions = db_session.scalar(
            sa.select(sa.func.count()).select_from(ItemVersion).where(
                ItemVersion.content_item_id == item.id
            )
        )
        assert versions == 1
