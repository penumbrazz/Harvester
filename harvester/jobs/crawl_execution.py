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

from harvester.adapters.binary_fetch import fetch_binary
from harvester.adapters.firecrawl import CrawlResult
from harvester.db.models import CrawlRun, CrawlTarget, RawObject, Recipe, Source
from harvester.domain.audit import write_audit
from harvester.domain.fetch_policy import check_fetch_policy
from harvester.domain.state import CRAWL_RUN_TRANSITIONS, transition_entity
from harvester.jobs.archive import ArchiveConfig, ArchiveWriter, ArchiveWriteResult
from harvester.jobs.repository import create_job

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


def execute_adapter_crawl(url: str, *, executor: str = "firecrawl") -> CrawlResult:
    """Execute an adapter crawl for the given URL.

    Routes to the appropriate adapter based on the executor type.
    Falls back to FirecrawlAdapter for unknown executors.
    """
    if executor == "playwright":
        from harvester.adapters.playwright import PlaywrightAdapter

        adapter = PlaywrightAdapter.from_env()
        return adapter.crawl(url)

    from harvester.adapters.firecrawl import FirecrawlAdapter

    adapter = FirecrawlAdapter.from_env()
    return adapter.crawl(url)


def write_archive(
    payload: bytes,
    source_id: uuid.UUID,
    crawl_run_id: uuid.UUID,
    content_type: str,
    original_url: str | None = None,
    category: str | None = None,
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
        original_url=original_url,
        category_override=category,
    )


def execute_crawl(
    session: Session,
    *,
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    actor: str = "system",
    topic_watch_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
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

    target: CrawlTarget | None = None
    crawl_url = source.url
    if target_id is not None:
        target = session.get(CrawlTarget, target_id)
        if target is None:
            raise CrawlExecutionError(f"CrawlTarget {target_id} not found")
        if target.source_id != source_id:
            raise CrawlExecutionError(
                f"CrawlTarget {target_id} does not belong to source {source_id}"
            )
        if target.recipe_id != recipe_id:
            raise CrawlExecutionError(
                f"CrawlTarget {target_id} does not belong to recipe {recipe_id}"
            )
        crawl_url = target.target_url

    logger.info(
        "crawl.start source=%s recipe=%s target=%s url=%s actor=%s",
        source_id,
        recipe_id,
        target_id,
        crawl_url,
        actor,
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
        if target is not None:
            _mark_target_running(target)
            session.flush()

        policy = check_fetch_policy(crawl_url)
        if not policy.allowed:
            reason = f"Fetch policy denied: {policy.reason}"
            logger.warning("crawl.policy_denied run=%s %s", run_id, reason)
            _fail_crawl_run(session, crawl_run, reason)
            if target is not None:
                _fail_crawl_target(target, reason)
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
        logger.info("crawl.running run=%s fetching %s", run_id, crawl_url)

        # 6. Execute fetch (binary for PDF targets, adapter crawl otherwise)
        is_pdf_target = target is not None and target.media_type == "pdf"

        if is_pdf_target:
            binary_result = fetch_binary(crawl_url)
            if binary_result.error:
                logger.error(
                    "crawl.binary_failed run=%s error=%s",
                    run_id,
                    binary_result.error,
                )
                _fail_crawl_run(session, crawl_run, binary_result.error)
                if target is not None:
                    _fail_crawl_target(target, binary_result.error)
                write_audit(
                    session,
                    actor=actor,
                    action="crawl_binary_failed",
                    entity_type="crawl_run",
                    entity_id=run_id,
                    reason=binary_result.error,
                )
                session.commit()
                raise CrawlExecutionError(binary_result.error, retryable=True)

            # Check redirect target policy
            if binary_result.final_url and binary_result.final_url != crawl_url:
                redirect_policy = check_fetch_policy(binary_result.final_url)
                if not redirect_policy.allowed:
                    reason = f"Redirect target denied: {redirect_policy.reason}"
                    logger.warning("crawl.redirect_denied run=%s %s", run_id, reason)
                    _fail_crawl_run(session, crawl_run, reason)
                    if target is not None:
                        _fail_crawl_target(target, reason)
                    session.commit()
                    return CrawlExecutionResult(
                        crawl_run_id=run_id,
                        status="failed",
                        error_message=reason,
                    )

            # Enforce payload size before archiving
            pdf_payload_bytes = binary_result.payload_bytes or b""
            max_bytes = _get_max_payload_bytes()
            if len(pdf_payload_bytes) > max_bytes:
                reason = (
                    f"Payload size {len(pdf_payload_bytes)} bytes "
                    f"exceeds maximum {max_bytes} bytes"
                )
                logger.warning("crawl.oversized run=%s %s", run_id, reason)
                _fail_crawl_run(session, crawl_run, reason)
                if target is not None:
                    _fail_crawl_target(target, reason)
                session.commit()
                return CrawlExecutionResult(
                    crawl_run_id=run_id,
                    status="failed",
                    error_message=reason,
                )

            pdf_content_type = binary_result.content_type or "application/pdf"
            logger.info(
                "crawl.archiving run=%s payload_size=%d content_type=%s",
                run_id,
                len(pdf_payload_bytes),
                pdf_content_type,
            )
            archive_result = write_archive(
                payload=pdf_payload_bytes,
                source_id=source_id,
                crawl_run_id=run_id,
                content_type=pdf_content_type,
                original_url=crawl_url,
                category=target.category if target else None,
            )
            content_type = pdf_content_type
            status_code = binary_result.status_code
        else:
            crawl_result = execute_adapter_crawl(crawl_url, executor=recipe.executor)

            if crawl_result.error:
                logger.error(
                    "crawl.adapter_failed run=%s error=%s",
                    run_id,
                    crawl_result.error,
                )
                _fail_crawl_run(session, crawl_run, crawl_result.error)
                if target is not None:
                    _fail_crawl_target(target, crawl_result.error)
                write_audit(
                    session,
                    actor=actor,
                    action="crawl_adapter_failed",
                    entity_type="crawl_run",
                    entity_id=run_id,
                    reason=crawl_result.error,
                )
                session.commit()
                raise CrawlExecutionError(crawl_result.error, retryable=True)

            # Check redirect target policy
            if crawl_result.final_url and crawl_result.final_url != crawl_url:
                redirect_policy = check_fetch_policy(crawl_result.final_url)
                if not redirect_policy.allowed:
                    reason = f"Redirect target denied: {redirect_policy.reason}"
                    logger.warning("crawl.redirect_denied run=%s %s", run_id, reason)
                    _fail_crawl_run(session, crawl_run, reason)
                    if target is not None:
                        _fail_crawl_target(target, reason)
                    session.commit()
                    return CrawlExecutionResult(
                        crawl_run_id=run_id,
                        status="failed",
                        error_message=reason,
                    )

            payload_bytes = (crawl_result.payload_text or "").encode("utf-8")
            logger.info(
                "crawl.archiving run=%s payload_size=%d content_type=%s",
                run_id,
                len(payload_bytes),
                crawl_result.content_type,
            )
            archive_result = write_archive(
                payload=payload_bytes,
                source_id=source_id,
                crawl_run_id=run_id,
                content_type=crawl_result.content_type or "text/html",
                original_url=crawl_url,
                category=target.category if target else None,
            )
            final_url = crawl_result.final_url
            content_type = crawl_result.content_type or "text/html"
            status_code = crawl_result.status_code

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

        if target is not None:
            _complete_crawl_target(
                target,
                raw_object_id=raw_id,
                final_url=final_url,
            )

        # 10. Update crawl_run with success
        crawl_run.raw_object_id = raw_id
        crawl_run.http_status = status_code
        crawl_run.content_type = content_type
        crawl_run.fetch_fingerprint = archive_result.content_hash

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
                "final_url": final_url,
                "http_status": status_code,
                "target_id": str(target_id) if target_id else None,
            },
        )

        # 11. Create extraction job
        create_job(
            session,
            job_type="extract",
            payload={"raw_object_id": str(raw_id)},
            source_id=str(source_id),
            auto_commit=False,
        )
        logger.info("crawl.enqueued_extract run=%s raw=%s", run_id, raw_id)

        session.commit()
        logger.info(
            "crawl.completed run=%s raw_object=%s http_status=%s bytes=%d",
            run_id,
            raw_id,
            status_code,
            archive_result.byte_size,
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
        if target is not None:
            _fail_crawl_target(target, str(exc))
        session.commit()
        raise CrawlExecutionError(str(exc), retryable=True) from exc


def _fail_crawl_run(session: Session, crawl_run: CrawlRun, error_message: str) -> None:
    """Mark a crawl run as failed with an error message."""
    if crawl_run.status != "failed":
        crawl_run.status = "failed"
    crawl_run.error_message = error_message
    crawl_run.completed_at = datetime.now(UTC)


def _mark_target_running(target: CrawlTarget) -> None:
    """Mark a crawl target as running before fetching."""
    target.status = "running"
    target.updated_at = datetime.now(UTC)


def _complete_crawl_target(
    target: CrawlTarget,
    *,
    raw_object_id: uuid.UUID,
    final_url: str | None,
) -> None:
    """Mark a crawl target as completed after a successful fetch."""
    target.status = "completed"
    target.last_raw_object_id = raw_object_id
    target.final_url = final_url
    target.last_error = None
    target.updated_at = datetime.now(UTC)


def _fail_crawl_target(target: CrawlTarget, error_message: str) -> None:
    """Mark a crawl target as failed and record diagnostic context."""
    target.status = "failed"
    target.failure_count += 1
    target.last_error = error_message
    target.updated_at = datetime.now(UTC)


def _get_max_payload_bytes() -> int:
    """Read max payload bytes from archive config."""
    from harvester.jobs.archive import ArchiveConfig

    return ArchiveConfig.from_env().max_payload_bytes
