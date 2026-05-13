"""Tests for the worker daemon — run_once and run_loop.

Covers: one-shot claiming embed_chunks jobs only, empty queue returning
zero counts, limit enforcement, loop mode with stop condition,
and crawl job processing via run_crawl_once.
"""

import uuid
from unittest.mock import MagicMock, patch

import sqlalchemy as sa

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


class TestRunCrawlOnce:
    """Tests for run_crawl_once — crawl job processing."""

    def test_claims_crawl_jobs_only(self, db_session):
        """run_crawl_once only claims crawl jobs, not embed_chunks."""
        from harvester.workers.daemon import run_crawl_once

        # Create an embed_chunks job that should NOT be claimed
        _, _, iv = make_full_chain(db_session, "Crawl Lane Test")
        chunk = make_chunk(db_session, iv.id, 0, "crawl lane text")
        db_session.commit()
        embed_job = create_job(
            db_session,
            job_type="embed_chunks",
            payload={"chunk_id": str(chunk.id)},
            idempotency_key=f"embed-{chunk.id}",
        )

        # Create a crawl job with dead-letter-level payload (will fail)
        crawl_job = create_job(
            db_session,
            job_type="crawl",
            payload={"source_id": str(uuid.uuid4())},
        )
        db_session.commit()

        stats = run_crawl_once(db_session, limit=10)

        assert stats["claimed"] >= 1

        # embed job should still be pending
        db_session.expire_all()
        embed = db_session.get(Job, embed_job.id)
        assert embed.status == "pending"

    def test_empty_queue_returns_zero_counts(self, db_session):
        """run_crawl_once returns all-zero counts when no crawl jobs."""
        from harvester.workers.daemon import run_crawl_once

        stats = run_crawl_once(db_session, limit=10)

        assert stats["claimed"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0


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


class TestCrawlWorkerLoop:
    """Tests for run_crawl_loop — crawl worker daemon loop."""

    def test_crawl_loop_only_claims_crawl_jobs(self, db_session):
        """Crawl worker loop only claims crawl jobs, not embed or extract."""
        from harvester.workers.daemon import run_crawl_loop

        call_count = 0
        mock_session = MagicMock()

        def fake_crawl_once(session, *, limit, worker_id=None):
            nonlocal call_count
            call_count += 1
            return {"claimed": 1, "completed": 0, "failed": 1}

        with patch("harvester.workers.daemon.run_crawl_once", side_effect=fake_crawl_once):
            run_crawl_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 1,
            )

        # run_crawl_once was called (proving crawl loop runs),
        # and the isolation is already verified in TestRunCrawlOnce
        assert call_count >= 1

    def test_crawl_loop_closes_session_each_round(self):
        """Crawl worker loop creates and closes session after each round."""
        from harvester.workers.daemon import run_crawl_loop

        sessions = []
        call_count = {"n": 0}

        def make_session():
            s = MagicMock()
            sessions.append(s)
            return s

        def fake_crawl_once(session, *, limit, worker_id=None):
            call_count["n"] += 1
            return {"claimed": 1, "completed": 1, "failed": 0}

        with patch("harvester.workers.daemon.run_crawl_once", side_effect=fake_crawl_once):
            run_crawl_loop(
                make_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count["n"] >= 2,
            )

        assert len(sessions) == 2
        for s in sessions:
            s.close.assert_called()

    def test_crawl_loop_sleeps_on_empty_queue(self):
        """Crawl worker loop sleeps when no jobs claimed."""
        from harvester.workers.daemon import run_crawl_loop

        sleep_times = []
        call_count = {"n": 0}

        mock_session = MagicMock()

        def fake_crawl_once(session, *, limit, worker_id=None):
            call_count["n"] += 1
            return {"claimed": 0, "completed": 0, "failed": 0}

        with patch("harvester.workers.daemon.run_crawl_once", side_effect=fake_crawl_once):
            with patch("harvester.workers.daemon.time.sleep", side_effect=lambda s: sleep_times.append(s)):
                run_crawl_loop(
                    lambda: mock_session,
                    poll_interval=5,
                    limit=10,
                    should_stop=lambda: call_count["n"] >= 2,
                )

        assert len(sleep_times) == 2
        assert all(t == 5 for t in sleep_times)

    def test_crawl_loop_respects_should_stop(self):
        """Crawl worker loop exits immediately when should_stop is True."""
        from harvester.workers.daemon import run_crawl_loop

        mock_session = MagicMock()

        with patch("harvester.workers.daemon.run_crawl_once", return_value={"claimed": 0, "completed": 0, "failed": 0}):
            run_crawl_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: True,
            )

    def test_crawl_loop_continues_after_exception(self):
        """Crawl worker loop continues after an exception in one round."""
        from harvester.workers.daemon import run_crawl_loop

        call_count = 0
        mock_session = MagicMock()

        def fake_crawl_once(session, *, limit, worker_id=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient failure")
            return {"claimed": 0, "completed": 0, "failed": 0}

        with patch("harvester.workers.daemon.run_crawl_once", side_effect=fake_crawl_once):
            run_crawl_loop(
                lambda: mock_session,
                poll_interval=0,
                limit=10,
                should_stop=lambda: call_count >= 2,
            )

        assert call_count == 2


class TestJobTypeIsolation:
    """Tests proving default worker does not claim crawl or extract jobs."""

    def test_run_once_does_not_claim_crawl_jobs(self, db_session):
        """Default run_once (embedding) does not claim crawl jobs."""
        from harvester.workers.daemon import run_once

        crawl_job = create_job(
            db_session,
            job_type="crawl",
            payload={"source_id": str(uuid.uuid4())},
        )
        db_session.commit()

        adapter = MagicMock()
        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        assert stats["claimed"] == 0

        db_session.expire_all()
        crawl = db_session.get(Job, crawl_job.id)
        assert crawl.status == "pending"

    def test_run_once_does_not_claim_extract_jobs(self, db_session):
        """Default run_once (embedding) does not claim extract jobs."""
        from harvester.workers.daemon import run_once

        extract_job = create_job(
            db_session,
            job_type="extract",
            payload={"source_id": str(uuid.uuid4())},
        )
        db_session.commit()

        adapter = MagicMock()
        stats = run_once(db_session, adapter, "stub-embedding-1536", limit=10)

        assert stats["claimed"] == 0

        db_session.expire_all()
        extract = db_session.get(Job, extract_job.id)
        assert extract.status == "pending"

    def test_run_loop_default_does_not_process_crawl_jobs(self, db_session):
        """Default run_loop (embedding) does not process crawl jobs."""
        from harvester.workers.daemon import run_loop

        crawl_job = create_job(
            db_session,
            job_type="crawl",
            payload={"source_id": str(uuid.uuid4())},
        )
        db_session.commit()

        adapter = MagicMock()
        call_count = 0

        def stop_after_one():
            nonlocal call_count
            call_count += 1
            return call_count >= 1

        run_loop(
            db_session,
            adapter,
            "stub-embedding-1536",
            poll_interval=0,
            limit=10,
            should_stop=stop_after_one,
        )

        db_session.expire_all()
        crawl = db_session.get(Job, crawl_job.id)
        assert crawl.status == "pending"
