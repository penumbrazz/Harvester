"""Tests for the worker daemon — run_once and run_loop.

Covers: one-shot claiming embed_chunks jobs only, empty queue returning
zero counts, limit enforcement, and loop mode with stop condition.
"""

from unittest.mock import MagicMock

from harvester.db.models import Job
from harvester.jobs.repository import create_job
from tests.workers.conftest import make_chunk, make_full_chain


class TestRunOnce:
    """Tests for run_once — one-shot worker."""

    def test_claims_embed_chunks_jobs_only(self, db_session):
        """One-shot worker only claims embed_chunks jobs, not other types."""
        from harvester.workers.daemon import run_once

        _, _, iv = make_full_chain(db_session, "Lane Test")
        chunk = make_chunk(db_session, iv.id, 0, "lane test text")
        db_session.commit()

        embed_job = create_job(
            db_session,
            job_type="embed_chunks",
            payload={
                "item_version_id": str(iv.id),
                "chunk_id": str(chunk.id),
            },
            idempotency_key=f"embed-{chunk.id}",
        )
        other_job = create_job(
            db_session,
            job_type="crawl",
            payload={"url": "https://example.com"},
        )
        db_session.commit()

        adapter = MagicMock()
        adapter.embed.return_value = [0.1] * 1536

        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        assert stats["claimed"] >= 1
        assert stats["completed"] >= 1

        # Other job should still be pending
        db_session.expire_all()
        other = db_session.get(Job, other_job.id)
        assert other.status == "pending"

    def test_empty_queue_returns_zero_counts(self, db_session):
        """One-shot worker returns all-zero counts when no jobs are available."""
        from harvester.workers.daemon import run_once

        adapter = MagicMock()
        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        assert stats["claimed"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0

    def test_limit_caps_claimed_jobs(self, db_session):
        """One-shot worker respects the limit parameter."""
        from harvester.workers.daemon import run_once

        _, _, iv = make_full_chain(db_session, "Limit Test")

        for i in range(5):
            chunk = make_chunk(db_session, iv.id, i, f"chunk {i}")
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

        adapter = MagicMock()
        adapter.embed.return_value = [0.1] * 1536

        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=2)

        assert stats["claimed"] == 2
        assert stats["completed"] == 2

    def test_failed_job_counted_correctly(self, db_session):
        """Failed jobs are counted in the 'failed' stat, not 'completed'."""
        from harvester.workers.daemon import run_once

        _, _, iv = make_full_chain(db_session, "Fail Count")
        chunk = make_chunk(db_session, iv.id, 0, "will fail")
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

        class BadAdapter:
            def embed(self, text: str) -> list[float]:
                raise RuntimeError("fail")

        stats = run_once(db_session, BadAdapter(), "bad-model", limit=10)

        assert stats["claimed"] == 1
        assert stats["completed"] == 0
        assert stats["failed"] == 1


class TestRunLoop:
    """Tests for run_loop — continuous worker."""

    def test_loop_calls_run_once_repeatedly(self, db_session):
        """Loop worker calls run_once repeatedly and stops on condition."""
        from harvester.workers.daemon import run_loop

        adapter = MagicMock()
        adapter.embed.return_value = [0.1] * 1536

        call_count = 0

        def stop_after_two(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count >= 2

        run_loop(
            db_session,
            adapter,
            "stub-embedding-1536",
            poll_interval=0,
            limit=5,
            should_stop=stop_after_two,
        )

        assert call_count >= 2
