"""Queue status API endpoint — aggregated job queue statistics and job list."""

from __future__ import annotations

from datetime import datetime

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import Job

router = APIRouter(prefix="/queue", tags=["queue"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class QueueStatusItem(BaseModel):
    job_type: str
    status: str
    count: int


class JobItem(BaseModel):
    """A single job record for the list view."""

    id: str
    job_type: str
    status: str
    priority: int
    attempts: int
    max_attempts: int
    run_after: datetime | None = None
    locked_by: str | None = None
    locked_until: datetime | None = None
    lane: str | None = None
    source_id: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Paginated job list response."""

    items: list[JobItem]
    total: int
    limit: int
    offset: int


@router.get("/status", response_model=list[QueueStatusItem])
def get_queue_status(
    _token: str = _Token,
    session: Session = _Session,
):
    """Return job queue counts aggregated by job_type and status.

    Does NOT return raw payload data.
    """
    rows = session.execute(
        text(
            "SELECT job_type, status, COUNT(*) as cnt "
            "FROM jobs "
            "GROUP BY job_type, status "
            "ORDER BY job_type, status"
        )
    ).fetchall()
    return [
        QueueStatusItem(job_type=row[0], status=row[1], count=row[2])
        for row in rows
    ]


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    job_type: str | None = Query(None, description="Filter by job type"),
    status: str | None = Query(None, description="Filter by status"),
    lane: str | None = Query(None, description="Filter by lane"),
    source_id: str | None = Query(None, description="Filter by source ID"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    _token: str = _Token,
    session: Session = _Session,
):
    """Return a paginated list of jobs with filter support.

    Does NOT return raw payload data.
    """
    query = session.query(Job)

    if job_type:
        query = query.filter(Job.job_type == job_type)
    if status:
        query = query.filter(Job.status == status)
    if lane:
        query = query.filter(Job.lane == lane)
    if source_id:
        try:
            query = query.filter(Job.source_id == str(uuid.UUID(source_id)))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid source_id UUID format"
            ) from None

    total = query.count()
    rows = (
        query.order_by(desc(Job.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        JobItem(
            id=str(j.id),
            job_type=j.job_type,
            status=j.status,
            priority=j.priority,
            attempts=j.attempts,
            max_attempts=j.max_attempts,
            run_after=j.run_after,
            locked_by=j.locked_by,
            locked_until=j.locked_until,
            lane=j.lane,
            source_id=j.source_id,
            last_error=j.last_error,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in rows
    ]

    return JobListResponse(items=items, total=total, limit=limit, offset=offset)
