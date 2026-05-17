"""Worker daemon — run_once and run_loop for embed_chunks jobs."""

from __future__ import annotations

import logging
import os
import socket
import time
from collections.abc import Callable
from functools import partial

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from harvester.db.settings import DatabaseSettings
from harvester.jobs.repository import claim_next_jobs, fail_job
from harvester.workers.crawl import process_crawl_job
from harvester.workers.embedding import process_embed_chunks_job
from harvester.workers.extraction import process_extract_job

logger = logging.getLogger(__name__)

_EMBED_LANES = ["embed_chunks"]
_CRAWL_LANES = ["crawl"]
_EXTRACT_LANES = ["extract"]


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


def _run_lane_once(
    session: Session,
    lanes: list[str],
    handler: Callable[[Session, object], bool],
    error_label: str,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of jobs from the given lanes.

    Parameters
    ----------
    session : Session
        Active database session.
    lanes : list[str]
        Lane tags to claim jobs from.
    handler : Callable[[Session, Job], bool]
        Function that processes a single job. Returns True on success.
    error_label : str
        Label used in error log messages (e.g. ``"crawl"``, ``"extract"``).
    limit : int
        Maximum number of jobs to claim in this batch.
    worker_id : str or None
        Worker identifier for job claiming.

    Returns
    -------
    dict[str, int]
        Processing stats with keys ``claimed``, ``completed``, ``failed``.
    """
    wid = worker_id or _default_worker_id()
    jobs = claim_next_jobs(session, wid, limit=limit, lanes=lanes)

    completed = 0
    failed = 0

    for job in jobs:
        try:
            success = handler(session, job)
            if success:
                completed += 1
            else:
                failed += 1
        except Exception as exc:
            logger.error(
                "Unhandled error processing %s job %s: %s", error_label, job.id, exc
            )
            failed += 1
            try:
                session.rollback()
                fail_job(
                    session, job.id, f"Unhandled {error_label} worker error: {exc}"
                )
            except Exception:
                logger.exception(
                    "Failed to dead-letter %s job %s after unhandled error",
                    error_label,
                    job.id,
                )

    return {
        "claimed": len(jobs),
        "completed": completed,
        "failed": failed,
    }


def _run_lane_loop(
    session_factory: Callable[[], Session],
    run_once_fn: Callable[..., dict[str, int]],
    lane_label: str,
    *,
    poll_interval: int = 10,
    limit: int = 10,
    worker_id: str | None = None,
    should_stop: Callable[[], bool] | None = None,
    **run_once_kwargs: object,
) -> None:
    """Generic daemon loop for any job lane.

    Each iteration creates a new session, calls *run_once_fn*, closes the
    session, and sleeps if no jobs were claimed.

    Parameters
    ----------
    session_factory : Callable
        Factory that returns a new Session per iteration.
    run_once_fn : Callable
        The ``run_*_once`` function to call each iteration.
    lane_label : str
        Label used in log messages.
    poll_interval : int
        Seconds to sleep when no jobs are claimed.
    limit : int
        Max jobs per iteration.
    worker_id : str or None
        Worker identifier.
    should_stop : Callable or None
        Optional callable that returns True to stop the loop.
    **run_once_kwargs
        Extra keyword arguments forwarded to *run_once_fn*.
    """
    wid = worker_id or _default_worker_id()

    while True:
        if should_stop and should_stop():
            logger.info("%s daemon stop condition met, exiting loop", lane_label)
            break

        sess: Session | None = None
        stats: dict[str, int] = {"claimed": 0}
        try:
            sess = session_factory()
            stats = run_once_fn(sess, limit=limit, worker_id=wid, **run_once_kwargs)
            logger.info(
                "%s daemon round complete: claimed=%d completed=%d failed=%d",
                lane_label,
                stats["claimed"],
                stats["completed"],
                stats["failed"],
            )
        except Exception as exc:
            logger.error("%s daemon round failed: %s", lane_label, exc)
            if sess is not None:
                try:
                    sess.rollback()
                except Exception:
                    logger.exception(
                        "Failed to rollback after %s worker error", lane_label.lower()
                    )
        finally:
            if sess is not None:
                sess.close()

        if stats["claimed"] == 0:
            logger.debug(
                "%s daemon: no jobs claimed, sleeping %ds", lane_label, poll_interval
            )
            time.sleep(poll_interval)

        if should_stop and should_stop():
            logger.info(
                "%s daemon stop condition met after iteration, exiting loop", lane_label
            )
            break


# ---------------------------------------------------------------------------
# Public lane-specific entry points
# ---------------------------------------------------------------------------


def run_once(
    session: Session,
    adapter,
    model_name: str,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of embed_chunks jobs."""
    handler = partial(process_embed_chunks_job, adapter=adapter, model_name=model_name)
    return _run_lane_once(
        session, _EMBED_LANES, handler, "embed", limit=limit, worker_id=worker_id
    )


def run_crawl_once(
    session: Session,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of crawl jobs."""
    return _run_lane_once(
        session,
        _CRAWL_LANES,
        process_crawl_job,
        "crawl",
        limit=limit,
        worker_id=worker_id,
    )


def run_extract_once(
    session: Session,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of extract jobs."""
    return _run_lane_once(
        session,
        _EXTRACT_LANES,
        process_extract_job,
        "extract",
        limit=limit,
        worker_id=worker_id,
    )


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
    """Run the embedding worker in a loop."""
    factory = (
        session_factory
        if callable(session_factory) and not isinstance(session_factory, Session)
        else lambda sf=session_factory: sf
    )
    _run_lane_loop(
        factory,
        run_once,
        "Embedding",
        poll_interval=poll_interval,
        limit=limit,
        worker_id=worker_id,
        should_stop=should_stop,
        adapter=adapter,
        model_name=model_name,
    )


def run_crawl_loop(
    session_factory: Callable[[], Session],
    *,
    poll_interval: int = 10,
    limit: int = 10,
    worker_id: str | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Run the crawl worker in a loop for daemon mode."""
    _run_lane_loop(
        session_factory,
        run_crawl_once,
        "Crawl",
        poll_interval=poll_interval,
        limit=limit,
        worker_id=worker_id,
        should_stop=should_stop,
    )


def run_extract_once(
    session: Session,
    *,
    limit: int = 10,
    worker_id: str | None = None,
) -> dict[str, int]:
    """Claim and process a batch of extract jobs."""
    return _run_lane_once(
        session,
        _EXTRACT_LANES,
        process_extract_job,
        "extract",
        limit=limit,
        worker_id=worker_id,
    )


def run_extract_loop(
    session_factory: Callable[[], Session],
    *,
    poll_interval: int = 10,
    limit: int = 10,
    worker_id: str | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Run the extract worker in a loop for daemon mode."""
    _run_lane_loop(
        session_factory,
        run_extract_once,
        "Extract",
        poll_interval=poll_interval,
        limit=limit,
        worker_id=worker_id,
        should_stop=should_stop,
    )
