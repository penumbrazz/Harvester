"""Failure inspection API endpoints — crawl runs, jobs, and targets."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import CrawlRun, CrawlTarget, Job

router = APIRouter(prefix="/failures", tags=["failures"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class FailureItem(BaseModel):
    id: str
    entity_type: str
    status: str
    error_message: str | None
    created_at: datetime


class FailedTargetItem(BaseModel):
    id: str
    target_url: str
    target_role: str
    media_type: str
    status: str
    failure_count: int
    last_error: str | None
    created_at: datetime


class FailuresResponse(BaseModel):
    crawl_runs: list[FailureItem]
    jobs: list[FailureItem]
    targets: list[FailedTargetItem]


@router.get("/recent", response_model=FailuresResponse)
def get_recent_failures(
    limit: int = 20,
    _token: str = _Token,
    session: Session = _Session,
):
    """Return recent failed crawl runs, jobs, and targets."""
    failed_crawls = (
        session.query(CrawlRun)
        .filter(CrawlRun.status == "failed")
        .order_by(desc(CrawlRun.created_at))
        .limit(limit)
        .all()
    )

    failed_jobs = (
        session.query(Job)
        .filter(Job.status.in_(["failed", "dead"]))
        .order_by(desc(Job.created_at))
        .limit(limit)
        .all()
    )

    failed_targets = (
        session.query(CrawlTarget)
        .filter(CrawlTarget.status == "failed")
        .order_by(desc(CrawlTarget.updated_at))
        .limit(limit)
        .all()
    )

    return FailuresResponse(
        crawl_runs=[
            FailureItem(
                id=str(c.id),
                entity_type="crawl_run",
                status=c.status,
                error_message=c.error_message,
                created_at=c.created_at,
            )
            for c in failed_crawls
        ],
        jobs=[
            FailureItem(
                id=str(j.id),
                entity_type="job",
                status=j.status,
                error_message=j.last_error,
                created_at=j.created_at,
            )
            for j in failed_jobs
        ],
        targets=[
            FailedTargetItem(
                id=str(t.id),
                target_url=t.target_url,
                target_role=t.target_role,
                media_type=t.media_type,
                status=t.status,
                failure_count=t.failure_count,
                last_error=t.last_error,
                created_at=t.created_at,
            )
            for t in failed_targets
        ],
    )
