"""Tests for embedding job creation — harvester.search.embedding.

Embedding jobs are created ONLY for chunks with embedding_status='pending'.
Never create embedding jobs for raw payload.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, ContentItem, ItemVersion
from harvester.search.embedding import create_embedding_jobs


class TestCreateEmbeddingJobs:
    """Test suite for create_embedding_jobs()."""

    def _seed_item_version(
        self, session: Session, *, normalized_text: str = "sample text"
    ) -> tuple[ContentItem, ItemVersion]:
        """Insert a minimal source + content_item + item_version for testing."""
        source_id = uuid.uuid4()
        item_id = uuid.uuid4()
        version_id = uuid.uuid4()
        # Create the source first to satisfy FK constraint.
        session.execute(
            sa.text(
                "INSERT INTO sources "
                "(id, name, kind, status, trust_level, auth_required, failure_count, "
                "created_at, updated_at) "
                "VALUES (:id, :name, 'test', 'active', 'medium', false, 0, NOW(), NOW())"
            ),
            {"id": source_id, "name": f"test-source-{source_id.hex[:8]}"},
        )
        session.execute(
            sa.text(
                "INSERT INTO content_items "
                "(id, item_type, source_id, status, created_at, updated_at) "
                "VALUES (:id, 'article', :src, 'active', NOW(), NOW())"
            ),
            {"id": item_id, "src": source_id},
        )
        session.execute(
            sa.text(
                "INSERT INTO item_versions "
                "(id, content_item_id, content_hash, normalized_text, created_at) "
                "VALUES (:id, :ci, 'hash123', :txt, NOW())"
            ),
            {"id": version_id, "ci": item_id, "txt": normalized_text},
        )
        session.flush()
        item = session.get(ContentItem, item_id)
        version = session.get(ItemVersion, version_id)
        return item, version

    def _seed_chunk(
        self,
        session: Session,
        item_version_id: uuid.UUID,
        *,
        chunk_index: int = 0,
        text: str = "chunk text",
        embedding_status: str = "pending",
    ) -> Chunk:
        """Insert a chunk row for testing."""
        chunk_id = uuid.uuid4()
        session.execute(
            sa.text(
                "INSERT INTO chunks "
                "(id, item_version_id, chunk_index, text, embedding_status, created_at) "
                "VALUES (:id, :iv, :idx, :txt, :st, NOW())"
            ),
            {
                "id": chunk_id,
                "iv": item_version_id,
                "idx": chunk_index,
                "txt": text,
                "st": embedding_status,
            },
        )
        session.flush()
        return session.get(Chunk, chunk_id)

    def test_creates_jobs_for_pending_chunks(self, db_session: Session):
        """Jobs must be created for chunks with embedding_status='pending'."""
        _, version = self._seed_item_version(db_session)
        self._seed_chunk(db_session, version.id, embedding_status="pending")

        jobs = create_embedding_jobs(db_session, version.id)
        assert len(jobs) >= 1
        for job in jobs:
            assert job.job_type == "embed_chunks"
            assert job.payload["item_version_id"] == str(version.id)
            assert job.status == "pending"

    def test_no_jobs_for_embedded_chunks(self, db_session: Session):
        """Chunks with embedding_status='done' must NOT produce jobs."""
        _, version = self._seed_item_version(db_session)
        self._seed_chunk(db_session, version.id, embedding_status="done")

        jobs = create_embedding_jobs(db_session, version.id)
        assert len(jobs) == 0

    def test_no_jobs_when_no_chunks(self, db_session: Session):
        """If the item version has no chunks at all, no jobs are created."""
        _, version = self._seed_item_version(db_session)

        jobs = create_embedding_jobs(db_session, version.id)
        assert len(jobs) == 0

    def test_mixed_status_only_pending_get_jobs(self, db_session: Session):
        """Only pending chunks get jobs; done/failed chunks are skipped."""
        _, version = self._seed_item_version(db_session)
        self._seed_chunk(
            db_session,
            version.id,
            chunk_index=0,
            embedding_status="pending",
        )
        self._seed_chunk(
            db_session,
            version.id,
            chunk_index=1,
            embedding_status="done",
        )
        self._seed_chunk(
            db_session,
            version.id,
            chunk_index=2,
            embedding_status="pending",
        )

        jobs = create_embedding_jobs(db_session, version.id)
        assert len(jobs) == 2
        for job in jobs:
            assert job.job_type == "embed_chunks"

    def test_jobs_reference_correct_item_version(self, db_session: Session):
        """Each job payload must reference the correct item_version_id."""
        _, version = self._seed_item_version(db_session)
        self._seed_chunk(db_session, version.id, chunk_index=0)

        jobs = create_embedding_jobs(db_session, version.id)
        assert len(jobs) == 1
        assert jobs[0].payload["item_version_id"] == str(version.id)

    def test_never_creates_jobs_for_raw_payload(self, db_session: Session):
        """Embedding jobs must NOT reference raw_objects — only chunks.

        This is a contract test: verify that the payload references
        item_version_id, not raw_object_id or any raw payload field.
        """
        _, version = self._seed_item_version(db_session)
        self._seed_chunk(db_session, version.id)

        jobs = create_embedding_jobs(db_session, version.id)
        for job in jobs:
            assert "item_version_id" in job.payload
            assert "raw_object_id" not in job.payload
            assert "raw_payload" not in job.payload
