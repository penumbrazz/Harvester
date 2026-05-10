"""Integration test: embed_chunks job → worker → vector_search.

End-to-end verification that the embedding worker pipeline correctly
processes jobs and makes chunks searchable via vector search.
"""

from harvester.adapters.stub_model import StubModelAdapter
from harvester.jobs.repository import create_job
from harvester.workers.daemon import run_once
from tests.workers.conftest import make_chunk, make_full_chain


class TestEmbeddingWorkerPipeline:
    """Integration tests for the full embedding worker pipeline."""

    def test_worker_processes_job_and_chunk_becomes_ready(self, db_session):
        """Worker processes embed_chunks job: job completed, chunk ready, embedding non-empty."""
        from harvester.db.models import Chunk, Job

        _, _, iv = make_full_chain(db_session, "Pipeline Integration")
        chunk = make_chunk(db_session, iv.id, 0, "integration test chunk text")
        db_session.commit()

        create_job(
            db_session,
            job_type="embed_chunks",
            payload={
                "item_version_id": str(iv.id),
                "chunk_id": str(chunk.id),
            },
            idempotency_key=f"embed-{chunk.id}",
        )
        db_session.commit()

        adapter = StubModelAdapter()
        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        assert stats["claimed"] >= 1
        assert stats["completed"] >= 1

        db_session.expire_all()
        updated_chunk = db_session.get(Chunk, chunk.id)
        assert updated_chunk.embedding_status == "ready"
        assert updated_chunk.embedding is not None
        assert len(updated_chunk.embedding) == 1536

    def test_embedded_chunk_findable_via_vector_search(self, db_session):
        """After worker embeds a chunk, vector_search can find it."""
        from harvester.search.vector import vector_search

        _, _, iv = make_full_chain(db_session, "Vector Search Verify")
        chunk = make_chunk(db_session, iv.id, 0, "searchable chunk content")
        db_session.commit()

        create_job(
            db_session,
            job_type="embed_chunks",
            payload={
                "item_version_id": str(iv.id),
                "chunk_id": str(chunk.id),
            },
            idempotency_key=f"embed-{chunk.id}",
        )
        db_session.commit()

        adapter = StubModelAdapter()
        run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        query_embedding = adapter.embed("searchable chunk content")

        results = vector_search(db_session, query_embedding, limit=5)
        assert len(results) >= 1

        chunk_ids = {r["chunk_id"] for r in results}
        assert chunk.id in chunk_ids
