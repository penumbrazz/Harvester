"""Worker daemon — run_once and run_loop for embed_chunks jobs."""

from __future__ import annotations

import logging
import os
import socket
import time
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from harvester.db.settings import DatabaseSettings
from harvester.jobs.repository import claim_next_jobs, fail_job
from harvester.workers.crawl import process_crawl_job
from harvester.workers.embedding import process_embed_chunks_job

logger = logging.getLogger(__name__)

_EMBED_LANES = ["embed_chunks"]
_CRAWL_LANES = ["crawl"]


def _default_worker_id() -> str:
    """Generate a stable worker ID from hostname and PID."""
    return f"{socket.gethostname()}-{os.getpid()}"


class _EngineCache:
    """Process-level engine singleton to avoid creating one per iteration."""

    _instance: _EngineCache | None = None

    def __init__(self) -> None:
        settings = DatabaseSettings()
        self._engine = create_engine(settings.database_url)
        self._session_factory = sessionmaker(bind=self._engine)

    @classmethod
    def get(cls) -> _EngineCache:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def make_session(self) -> Session:
        return self._session_factory()

    def dispose(self) -> None:
        self._engine.dispose()
        _EngineCache._instance = None


def _make_session() -> Session:
    """Create a new database session using the process-level engine."""
    return _EngineCache.get().make_session()


def run_once(
    session: Session,
    adapter,
    model_name: str,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of embed_chunks jobs.

    Parameters
    ----------
    session : Session
        Active database session.
    adapter
        Embedding adapter with an ``embed(text)`` method.
    model_name : str
        Model identifier written into ``chunks.embedding_model``.
    limit : int
        Maximum number of jobs to claim in this batch.
    worker_id : str or None
        Worker identifier for job claiming. Generated if not provided.

    Returns
    -------
    dict[str, int]
        Processing stats with keys ``claimed``, ``completed``, ``failed``.
    """
    wid = worker_id or _default_worker_id()
    jobs = claim_next_jobs(session, wid, limit=limit, lanes=_EMBED_LANES)

    completed = 0
    failed = 0

    for job in jobs:
        try:
            success = process_embed_chunks_job(session, job, adapter, model_name)
            if success:
                completed += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error("Unhandled error processing job %s: %s", job.id, exc)
            failed += 1
            try:
                session.rollback()
                fail_job(session, job.id, f"Unhandled worker error: {exc}")
            except Exception:
                logger.exception(
                    "Failed to dead-letter job %s after unhandled error", job.id
                )

    return {
        "claimed": len(jobs),
        "completed": completed,
        "failed": failed,
    }


def run_crawl_once(
    session: Session,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of crawl jobs.

    Parameters
    ----------
    session : Session
        Active database session.
    limit : int
        Maximum number of jobs to claim in this batch.
    worker_id : str or None
        Worker identifier for job claiming. Generated if not provided.

    Returns
    -------
    dict[str, int]
        Processing stats with keys ``claimed``, ``completed``, ``failed``.
    """
    wid = worker_id or _default_worker_id()
    jobs = claim_next_jobs(session, wid, limit=limit, lanes=_CRAWL_LANES)

    completed = 0
    failed = 0

    for job in jobs:
        try:
            success = process_crawl_job(session, job)
            if success:
                completed += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error("Unhandled error processing crawl job %s: %s", job.id, exc)
            failed += 1
            try:
                session.rollback()
                fail_job(session, job.id, f"Unhandled crawl worker error: {exc}")
            except Exception:
                logger.exception(
                    "Failed to dead-letter crawl job %s after unhandled error", job.id
                )

    return {
        "claimed": len(jobs),
        "completed": completed,
        "failed": failed,
    }


def run_loop(
    session_factory: Callable[[], Session] | Session,
    adapter,
    model_name: str,
    *,
    poll_interval: int = 10,
    limit: int = 10,
    worker_id: str | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Run the embedding worker in a loop.

    Creates a new session for each iteration and properly closes it afterwards
    to avoid connection leaks in long-running Docker daemons.

    Parameters
    ----------
    session_factory : Callable or Session
        A factory that returns a new Session, or an existing Session.
    adapter
        Embedding adapter.
    model_name : str
        Model identifier.
    poll_interval : int
        Seconds to sleep between iterations when no jobs are claimed.
    limit : int
        Max jobs per iteration.
    worker_id : str or None
        Worker identifier.
    should_stop : Callable or None
        Optional callable that returns True to stop the loop.
    """
    wid = worker_id or _default_worker_id()
    use_factory = callable(session_factory) and not isinstance(
        session_factory, Session
    )

    while True:
        if should_stop and should_stop():
            logger.info("Stop condition met, exiting loop")
            break

        sess: Session | None = None
        stats: dict[str, int] = {"claimed": 0}
        try:
            if use_factory:
                sess = session_factory()
            else:
                sess = session_factory

            stats = run_once(
                sess, adapter, model_name, limit=limit, worker_id=wid
            )
        except Exception as exc:
            logger.error("Worker loop iteration failed: %s", exc)
        finally:
            if use_factory and sess is not None:
                sess.close()

        if stats["claimed"] == 0:
            logger.debug("No jobs claimed, sleeping %ds", poll_interval)
            time.sleep(poll_interval)

        if should_stop and should_stop():
            logger.info("Stop condition met after iteration, exiting loop")
            break
