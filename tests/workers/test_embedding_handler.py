"""Tests for the embed_chunks job handler.

Covers: successful embedding, ready-skip, adapter failure with retry and
terminal failure, invalid payload dead-letter, missing chunk dead-letter,
and embedding dimension validation.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, Job
from tests.workers.conftest import make_chunk, make_full_chain


def _insert_job(
    db_session: Session,
    *,
    payload: dict | None = None,
    **overrides,
) -> Job:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        job_type="embed_chunks",
        status="running",
        priority=0,
        attempts=0,
        max_attempts=3,
        payload=payload,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    db_session.flush()
    return job


class TestProcessEmbedChunksJob:
    """Tests for process_embed_chunks_job."""

    def test_success_writes_embedding_and_status(self, db_session):
        """Valid embed_chunks job reads chunk text, writes 1536-dim embedding,
        embedding_model, and embedding_status='ready'."""
        from harvester.adapters.stub_model import StubModelAdapter
        from harvester.workers.embedding import process_embed_chunks_job

        _, _, iv = make_full_chain(db_session, "Embed Test")
        chunk = make_chunk(db_session, iv.id, 0, "hello world")
        db_session.commit()

        job = _insert_job(
            db_session,
            payload={"item_version_id": str(iv.id), "chunk_id": str(chunk.id)},
        )
        db_session.commit()

        adapter = StubModelAdapter()
        result = process_embed_chunks_job(db_session, job, adapter, "stub-embedding-1536")

        assert result is True
        db_session.expire_all()
        updated = db_session.get(Chunk, chunk.id)
        assert updated.embedding_status == "ready"
        assert updated.embedding_model == "stub-embedding-1536"
        assert updated.embedding is not None
        assert len(updated.embedding) == 1536

        job_check = db_session.get(Job, job.id)
        assert job_check.status == "completed"

    def test_ready_chunk_skips_embedding(self, db_session):
        """Chunk with embedding_status='ready' is not re-embedded, job still completed."""
        from harvester.adapters.stub_model import StubModelAdapter
        from harvester.workers.embedding import process_embed_chunks_job

        _, _, iv = make_full_chain(db_session, "Ready Skip")
        chunk = make_chunk(db_session, iv.id, 0, "already done", embedding_status="ready")
        db_session.commit()

        job = _insert_job(
            db_session,
            payload={"item_version_id": str(iv.id), "chunk_id": str(chunk.id)},
        )
        db_session.commit()

        adapter = StubModelAdapter()
        result = process_embed_chunks_job(db_session, job, adapter, "stub-embedding-1536")

        assert result is True
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "completed"

    def test_adapter_exception_fails_job_chunk_stays_pending(self, db_session):
        """Adapter exception calls fail_job; chunk stays pending for retry."""
        from harvester.workers.embedding import process_embed_chunks_job

        _, _, iv = make_full_chain(db_session, "Adapter Fail")
        chunk = make_chunk(db_session, iv.id, 0, "will fail")
        db_session.commit()

        job = _insert_job(
            db_session,
            payload={"item_version_id": str(iv.id), "chunk_id": str(chunk.id)},
        )
        db_session.commit()

        class BadAdapter:
            def embed(self, text: str) -> list[float]:
                raise RuntimeError("model service unavailable")

        result = process_embed_chunks_job(db_session, job, BadAdapter(), "bad-model")

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "failed"

        db_session.expire_all()
        chunk_check = db_session.get(Chunk, chunk.id)
        assert chunk_check.embedding_status == "pending"

    def test_invalid_chunk_id_dead_letters(self, db_session):
        """Invalid chunk_id permanently dead-letters the job without retry."""
        from harvester.adapters.stub_model import StubModelAdapter
        from harvester.workers.embedding import process_embed_chunks_job

        job = _insert_job(
            db_session,
            payload={"chunk_id": "not-a-uuid"},
        )
        db_session.commit()

        adapter = StubModelAdapter()
        result = process_embed_chunks_job(db_session, job, adapter, "stub-embedding-1536")

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "dead"
        assert job_check.last_error is not None

    def test_missing_chunk_dead_letters(self, db_session):
        """Payload with a valid UUID that doesn't match any chunk dead-letters."""
        from harvester.adapters.stub_model import StubModelAdapter
        from harvester.workers.embedding import process_embed_chunks_job

        fake_chunk_id = str(uuid.uuid4())
        job = _insert_job(
            db_session,
            payload={"chunk_id": fake_chunk_id},
        )
        db_session.commit()

        adapter = StubModelAdapter()
        result = process_embed_chunks_job(db_session, job, adapter, "stub-embedding-1536")

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "dead"
        assert job_check.last_error is not None

    def test_terminal_failure_marks_chunk_failed(self, db_session):
        """When cumulative attempts reach max_attempts, chunk is marked failed."""
        from harvester.workers.embedding import process_embed_chunks_job

        _, _, iv = make_full_chain(db_session, "Terminal Fail")
        chunk = make_chunk(db_session, iv.id, 0, "terminal")
        db_session.commit()

        # attempts=2 means fail_job will increment to 3 >= max_attempts=3 → dead
        job = _insert_job(
            db_session,
            payload={"item_version_id": str(iv.id), "chunk_id": str(chunk.id)},
            attempts=2,
            max_attempts=3,
        )
        db_session.commit()

        class BadAdapter:
            def embed(self, text: str) -> list[float]:
                raise RuntimeError("permanent failure")

        result = process_embed_chunks_job(db_session, job, BadAdapter(), "bad-model")

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "dead"

        db_session.expire_all()
        chunk_check = db_session.get(Chunk, chunk.id)
        assert chunk_check.embedding_status == "failed"

    def test_wrong_embedding_dimension_fails_job(self, db_session):
        """Adapter returning wrong dimension fails the job."""
        from harvester.workers.embedding import process_embed_chunks_job

        _, _, iv = make_full_chain(db_session, "Dim Mismatch")
        chunk = make_chunk(db_session, iv.id, 0, "dimension test")
        db_session.commit()

        job = _insert_job(
            db_session,
            payload={"item_version_id": str(iv.id), "chunk_id": str(chunk.id)},
            attempts=2,
            max_attempts=3,
        )
        db_session.commit()

        class WrongDimAdapter:
            def embed(self, text: str) -> list[float]:
                return [0.1] * 768  # wrong dimension

        result = process_embed_chunks_job(
            db_session, job, WrongDimAdapter(), "wrong-dim"
        )

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "dead"
        assert "dimension" in job_check.last_error.lower()

    def test_missing_chunk_id_dead_letters(self, db_session):
        """Missing chunk_id in payload dead-letters the job."""
        from harvester.adapters.stub_model import StubModelAdapter
        from harvester.workers.embedding import process_embed_chunks_job

        job = _insert_job(db_session, payload={})
        db_session.commit()

        adapter = StubModelAdapter()
        result = process_embed_chunks_job(db_session, job, adapter, "stub-embedding-1536")

        assert result is False
        job_check = db_session.get(Job, job.id)
        assert job_check.status == "dead"
