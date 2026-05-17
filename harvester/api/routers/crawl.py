"""Crawl run API endpoints — execution, list view, and target summaries."""

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
from harvester.db.models import CrawlRun, CrawlTarget, Source
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
    source_name: str | None = None
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
            source_id,
            recipe_id,
            exc,
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
    query = session.query(CrawlRun, Source.name.label("source_name")).outerjoin(
        Source, CrawlRun.source_id == Source.id
    )

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
    rows = query.order_by(desc(CrawlRun.created_at)).offset(offset).limit(limit).all()

    items = [
        CrawlRunItem(
            id=str(r.CrawlRun.id),
            source_id=str(r.CrawlRun.source_id) if r.CrawlRun.source_id else None,
            source_name=r.source_name,
            recipe_id=str(r.CrawlRun.recipe_id) if r.CrawlRun.recipe_id else None,
            status=r.CrawlRun.status,
            http_status=r.CrawlRun.http_status,
            error_message=r.CrawlRun.error_message,
            raw_object_id=str(r.CrawlRun.raw_object_id)
            if r.CrawlRun.raw_object_id
            else None,
            started_at=r.CrawlRun.started_at,
            completed_at=r.CrawlRun.completed_at,
            created_at=r.CrawlRun.created_at,
        )
        for r in rows
    ]

    return CrawlRunListResponse(items=items, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Crawl Target summaries
# ---------------------------------------------------------------------------


class CrawlTargetItem(BaseModel):
    """A crawl target summary for the operations view — no raw payload."""

    id: str
    source_id: str
    target_url: str
    target_role: str
    media_type: str
    status: str
    depth: int
    priority: int = 0
    failure_count: int = 0
    last_error: str | None = None
    external_item_id: str | None = None
    final_url: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime | None = None


class CrawlTargetListResponse(BaseModel):
    items: list[CrawlTargetItem]
    total: int
    limit: int
    offset: int


@router.get("/targets", response_model=CrawlTargetListResponse)
def list_crawl_targets(
    source_id: str | None = Query(None, description="Filter by source ID"),
    target_role: str | None = Query(None, description="Filter by target role"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    _token: str = _Token,
    session: Session = _Session,
):
    """Return a paginated list of crawl targets with status and error info.

    Does NOT expose raw payload or internal storage fields.
    """
    query = session.query(CrawlTarget)

    if source_id:
        try:
            query = query.filter(CrawlTarget.source_id == uuid.UUID(source_id))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid source_id UUID format"
            ) from None
    if target_role:
        query = query.filter(CrawlTarget.target_role == target_role)
    if status:
        query = query.filter(CrawlTarget.status == status)

    total = query.count()
    rows = (
        query.order_by(desc(CrawlTarget.last_seen_at)).offset(offset).limit(limit).all()
    )

    items = [
        CrawlTargetItem(
            id=str(r.id),
            source_id=str(r.source_id),
            target_url=r.target_url,
            target_role=r.target_role,
            media_type=r.media_type,
            status=r.status,
            depth=r.depth,
            priority=r.priority,
            failure_count=r.failure_count,
            last_error=r.last_error,
            external_item_id=r.external_item_id,
            final_url=r.final_url,
            first_seen_at=r.first_seen_at,
            last_seen_at=r.last_seen_at,
        )
        for r in rows
    ]

    return CrawlTargetListResponse(items=items, total=total, limit=limit, offset=offset)
