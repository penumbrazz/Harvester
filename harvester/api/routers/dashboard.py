"""Dashboard summary API endpoint — aggregated system health metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class _CountByStatus(BaseModel):
    """Count of entities grouped by status."""

    total: int
    by_status: dict[str, int]


class DashboardSummary(BaseModel):
    """Aggregated dashboard summary with key metrics."""

    sources: _CountByStatus
    crawl_runs: _CountByStatus
    jobs: _CountByStatus
    content_items: _CountByStatus
    failures: _CountByStatus
    audit_events: _CountByStatus


# Allowed table/column pairs for safe dynamic query construction.
_ALLOWED_COUNT_QUERIES: dict[str, tuple[str, str]] = {
    "sources": ("sources", "status"),
    "crawl_runs": ("crawl_runs", "status"),
    "jobs": ("jobs", "status"),
    "content_items": ("content_items", "status"),
    "audit_events": ("audit_events", "action"),
}


def _count_by_column(session: Session, key: str) -> _CountByStatus:
    """Count rows in a table grouped by a column.

    Uses a whitelist to prevent SQL injection from dynamic table/column names.
    """
    if key not in _ALLOWED_COUNT_QUERIES:
        raise ValueError(f"Unknown count key: {key}")
    table, column = _ALLOWED_COUNT_QUERIES[key]
    rows = session.execute(
        text(f"SELECT {column}, COUNT(*) as cnt FROM {table} GROUP BY {column}")
    ).fetchall()
    by_status = {row[0]: row[1] for row in rows}
    total = sum(by_status.values())
    return _CountByStatus(total=total, by_status=by_status)


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    _token: str = _Token,
    session: Session = _Session,
):
    """Return aggregated dashboard metrics.

    Does NOT return raw payload data, only counts.
    """
    return DashboardSummary(
        sources=_count_by_column(session, "sources"),
        crawl_runs=_count_by_column(session, "crawl_runs"),
        jobs=_count_by_column(session, "jobs"),
        content_items=_count_by_column(session, "content_items"),
        failures=_count_failures(session),
        audit_events=_count_by_column(session, "audit_events"),
    )


def _count_failures(session: Session) -> _CountByStatus:
    """Count failed crawl runs and dead/failed jobs as failure metrics."""
    failed_crawls = session.execute(
        text("SELECT COUNT(*) FROM crawl_runs WHERE status = 'failed'")
    ).scalar()
    failed_jobs = session.execute(
        text("SELECT COUNT(*) FROM jobs WHERE status IN ('failed', 'dead')")
    ).scalar()
    total = (failed_crawls or 0) + (failed_jobs or 0)
    return _CountByStatus(
        total=total,
        by_status={
            "failed_crawl_runs": failed_crawls or 0,
            "failed_jobs": failed_jobs or 0,
        },
    )
