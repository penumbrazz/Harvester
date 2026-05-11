"""Crawl execution service for Harvester.

Orchestrates: source/recipe validation -> fetch policy -> adapter crawl ->
archive write -> raw_object metadata -> crawl_run status + audit events.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import CrawlRun, RawObject, Recipe, Source
from harvester.domain.audit import write_audit
from harvester.domain.fetch_policy import check_fetch_policy
from harvester.domain.state import CRAWL_RUN_TRANSITIONS, transition_entity
from harvester.jobs.archive import ArchiveConfig, ArchiveWriter, ArchiveWriteResult

logger = logging.getLogger(__name__)


class CrawlExecutionError(Exception):
    """Raised when crawl execution fails."""

    retryable: bool = False

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class CrawlExecutionResult:
    """Result of a crawl execution."""

    crawl_run_id: uuid.UUID
    status: str
    raw_object_id: uuid.UUID | None = None
    error_message: str | None = None


def execute_adapter_crawl(url: str) -> CrawlResult:
    """Execute an adapter crawl for the given URL.

    This function creates a Firecrawl adapter from environment config
    and performs the crawl. Separated for testability.
    """
    from harvester.adapters.firecrawl import FirecrawlAdapter

    adapter = FirecrawlAdapter.from_env()
    return adapter.crawl(url)


def write_archive(
    payload: bytes,
    source_id: uuid.UUID,
    crawl_run_id: uuid.UUID,
    content_type: str,
) -> ArchiveWriteResult:
    """Write payload to archive storage.

    Separated for testability.
    """

    config = ArchiveConfig.from_env()
    writer = ArchiveWriter(config)
    return writer.write(
        payload=payload,
        source_id=source_id,
        crawl_run_id=crawl_run_id,
        content_type=content_type,
    )


def execute_crawl(
    session: Session,
    *,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    actor: str = "system",
    topic_watch_id: uuid.UUID | None = None,
) -> CrawlExecutionResult:
    """Execute a public web crawl run.

    Steps:
    1. Validate source and recipe are approved
    2. Create a pending CrawlRun
    3. Check fetch policy on source URL
    4. Call adapter to crawl
    5. Write raw payload to archive
    6. Create raw_object metadata
    7. Update crawl_run with results

    Raises CrawlExecutionError on any validation or execution failure.
    """
    # 1. Validate source
    source = session.get(Source, source_id)
    if source is None:
        raise CrawlExecutionError(f"Source {source_id} not found")
    if source.status not in ("watched", "active"):
        raise CrawlExecutionError(
            f"Source {source_id} status is '{source.status}', not approved for crawl"
        )
    if not source.url:
        raise CrawlExecutionError(f"Source {source_id} has no URL configured")

    # 2. Validate recipe
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise CrawlExecutionError(f"Recipe {recipe_id} not found")
    if recipe.approval_status != "approved":
        raise CrawlExecutionError(
            f"Recipe {recipe_id} approval_status is '{recipe.approval_status}', not approved"
        )
    if recipe.risk_level == "high":
        raise CrawlExecutionError(
            f"Recipe {recipe_id} has high risk_level, not allowed for crawl"
        )

    logger.info(
        "crawl.start source=%s recipe=%s url=%s actor=%s",
        source_id, recipe_id, source.url, actor,
    )

    # 3. Create pending crawl run
    run_id = uuid.uuid4()
    now = datetime.now(UTC)
    crawl_run = CrawlRun(
        id=run_id,
        source_id=source_id,
        topic_watch_id=topic_watch_id,
        recipe_id=recipe_id,
        status="pending",
        started_at=now,
        created_at=now,
    )
    session.add(crawl_run)
    session.flush()

    try:
        # 4. Check fetch policy
        policy = check_fetch_policy(source.url)
        if not policy.allowed:
            reason = f"Fetch policy denied: {policy.reason}"
            logger.warning("crawl.policy_denied run=%s %s", run_id, reason)
            _fail_crawl_run(session, crawl_run, reason)
            write_audit(
                session,
                actor=actor,
                action="crawl_policy_denied",
                entity_type="crawl_run",
                entity_id=run_id,
                reason=policy.reason,
            )
            session.commit()
            return CrawlExecutionResult(
                crawl_run_id=run_id,
                status="failed",
                error_message=reason,
            )

        # 5. Transition to running
        transition_entity(
            session,
            crawl_run,
            CRAWL_RUN_TRANSITIONS,
            "running",
            actor,
            "crawl_run",
        )
        session.flush()
        logger.info("crawl.running run=%s fetching %s", run_id, source.url)

        # 6. Execute adapter crawl
        crawl_result = execute_adapter_crawl(source.url)

        if crawl_result.error:
            logger.error(
                "crawl.adapter_failed run=%s error=%s", run_id, crawl_result.error,
            )
            _fail_crawl_run(session, crawl_run, crawl_result.error)
            write_audit(
                session,
                actor=actor,
                action="crawl_adapter_failed",
                entity_type="crawl_run",
                entity_id=run_id,
                reason=crawl_result.error,
            )
            session.commit()
            raise CrawlExecutionError(
                crawl_result.error, retryable=True
            )

        # 7. Check redirect target policy
        if crawl_result.final_url and crawl_result.final_url != source.url:
            redirect_policy = check_fetch_policy(crawl_result.final_url)
            if not redirect_policy.allowed:
                reason = f"Redirect target denied: {redirect_policy.reason}"
                logger.warning("crawl.redirect_denied run=%s %s", run_id, reason)
                _fail_crawl_run(session, crawl_run, reason)
                session.commit()
                return CrawlExecutionResult(
                    crawl_run_id=run_id,
                    status="failed",
                    error_message=reason,
                )

        # 8. Write payload to archive
        payload_bytes = (crawl_result.payload_text or "").encode("utf-8")
        logger.info(
            "crawl.archiving run=%s payload_size=%d content_type=%s",
            run_id, len(payload_bytes), crawl_result.content_type,
        )
        archive_result = write_archive(
            payload=payload_bytes,
            source_id=source_id,
            crawl_run_id=run_id,
            content_type=crawl_result.content_type or "text/html",
        )

        # 9. Create raw_object metadata
        raw_id = uuid.uuid4()
        raw_object = RawObject(
            id=raw_id,
            source_id=source_id,
            content_type=archive_result.content_type,
            content_hash=archive_result.content_hash,
            storage_uri=archive_result.storage_uri,
            byte_size=archive_result.byte_size,
            retention_policy="raw",
            retain_until=archive_result.retain_until,
            compressed=False,
            created_at=datetime.now(UTC),
        )
        session.add(raw_object)
        session.flush()

        # 10. Update crawl_run with success
        crawl_run.raw_object_id = raw_id
        crawl_run.http_status = crawl_result.status_code
        crawl_run.content_type = crawl_result.content_type
        crawl_run.fetch_fingerprint = archive_result.content_hash

        if crawl_result.final_url:
            crawl_run.completed_at = datetime.now(UTC)

        transition_entity(
            session,
            crawl_run,
            CRAWL_RUN_TRANSITIONS,
            "completed",
            actor,
            "crawl_run",
        )

        write_audit(
            session,
            actor=actor,
            action="crawl_completed",
            entity_type="crawl_run",
            entity_id=run_id,
            after_state={
                "raw_object_id": str(raw_id),
                "final_url": crawl_result.final_url,
                "http_status": crawl_result.status_code,
            },
        )

        session.commit()
        logger.info(
            "crawl.completed run=%s raw_object=%s http_status=%s bytes=%d",
            run_id, raw_id, crawl_result.status_code, archive_result.byte_size,
        )
        return CrawlExecutionResult(
            crawl_run_id=run_id,
            status="completed",
            raw_object_id=raw_id,
        )

    except CrawlExecutionError:
        raise
    except Exception as exc:
        logger.exception("crawl.unexpected_error run=%s", run_id)
        _fail_crawl_run(session, crawl_run, str(exc))
        session.commit()
        raise CrawlExecutionError(str(exc), retryable=True) from exc


def _fail_crawl_run(session: Session, crawl_run: CrawlRun, error_message: str) -> None:
    """Mark a crawl run as failed with an error message."""
    if crawl_run.status != "failed":
        crawl_run.status = "failed"
    crawl_run.error_message = error_message
    crawl_run.completed_at = datetime.now(UTC)
