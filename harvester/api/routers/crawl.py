"""Crawl run API endpoints — execution and list view."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import CrawlRun
from harvester.jobs.crawl_execution import CrawlExecutionError, execute_crawl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class CrawlRunRequest(BaseModel):
    source_id: str
    recipe_id: str


class CrawlRunResponse(BaseModel):
    crawl_run_id: str
    status: str
    raw_object_id: str | None = None
    error_message: str | None = None


class CrawlRunItem(BaseModel):
    """A single crawl run record for the list view."""

    id: str
    source_id: str | None = None
    recipe_id: str | None = None
    status: str
    http_status: int | None = None
    error_message: str | None = None
    raw_object_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class CrawlRunListResponse(BaseModel):
    """Paginated crawl run list response."""

    items: list[CrawlRunItem]
    total: int
    limit: int
    offset: int


@router.post("/run", response_model=CrawlRunResponse)
def run_crawl(
    request: CrawlRunRequest,
    _token: str = _Token,
    session: Session = _Session,
):
    """Execute a public web crawl run for an approved source and recipe."""
    try:
        source_id = uuid.UUID(request.source_id)
        recipe_id = uuid.UUID(request.recipe_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from None

    try:
        result = execute_crawl(
            session=session,
            source_id=source_id,
            recipe_id=recipe_id,
            actor="api",
        )
    except CrawlExecutionError as exc:
        logger.warning(
            "crawl.run_failed source=%s recipe=%s error=%s",
            source_id, recipe_id, exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CrawlRunResponse(
        crawl_run_id=str(result.crawl_run_id),
        status=result.status,
        raw_object_id=str(result.raw_object_id) if result.raw_object_id else None,
        error_message=result.error_message,
    )


@router.get("/runs", response_model=CrawlRunListResponse)
def list_crawl_runs(
    status: str | None = Query(None, description="Filter by status"),
    source_id: str | None = Query(None, description="Filter by source ID"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    _token: str = _Token,
    session: Session = _Session,
):
    """Return a paginated list of crawl runs.

    Does NOT return raw HTML/API payload.
    """
    query = session.query(CrawlRun)

    if status:
        query = query.filter(CrawlRun.status == status)
    if source_id:
        try:
            query = query.filter(CrawlRun.source_id == uuid.UUID(source_id))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid source_id UUID format"
            ) from None

    total = query.count()
    rows = (
        query.order_by(desc(CrawlRun.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        CrawlRunItem(
            id=str(r.id),
            source_id=str(r.source_id) if r.source_id else None,
            recipe_id=str(r.recipe_id) if r.recipe_id else None,
            status=r.status,
            http_status=r.http_status,
            error_message=r.error_message,
            raw_object_id=str(r.raw_object_id) if r.raw_object_id else None,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return CrawlRunListResponse(items=items, total=total, limit=limit, offset=offset)
