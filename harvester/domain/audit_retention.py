"""Audit event retention and cleanup service."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 7


@dataclass(frozen=True)
class CleanupResult:
    """Result of an audit cleanup run."""

    deleted_count: int
    cutoff: datetime
    retention_days: int


def get_retention_days() -> int:
    """Read retention days from env, defaulting to 7.

    Raises ``ValueError`` for non-positive or non-integer values.
    """
    raw = os.environ.get("HARVESTER_AUDIT_RETENTION_DAYS", "").strip()
    if not raw:
        return DEFAULT_RETENTION_DAYS
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"HARVESTER_AUDIT_RETENTION_DAYS must be a positive integer, got: {raw!r}"
        ) from exc
    if value < 1:
        raise ValueError(f"HARVESTER_AUDIT_RETENTION_DAYS must be >= 1, got: {value}")
    return value


def cleanup_audit_events(
    session: Session, *, now: datetime | None = None
) -> CleanupResult:
    """Delete audit events older than the configured retention window.

    Parameters
    ----------
    session : Session
        Database session (caller is responsible for commit/rollback).
    now : datetime or None
        Reference timestamp; defaults to ``datetime.now(UTC)``.

    Returns
    -------
    CleanupResult
        Statistics about the cleanup run.
    """
    retention_days = get_retention_days()
    ref_time = now or datetime.now(UTC)
    cutoff = ref_time - timedelta(days=retention_days)

    result = session.execute(
        sa.text("DELETE FROM audit_events WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    deleted_count = result.rowcount

    logger.info(
        "Audit cleanup: retention_days=%d cutoff=%s deleted=%d",
        retention_days,
        cutoff.isoformat(),
        deleted_count,
    )

    return CleanupResult(
        deleted_count=deleted_count,
        cutoff=cutoff,
        retention_days=retention_days,
    )
