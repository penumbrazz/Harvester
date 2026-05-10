"""Crawl run API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.jobs.crawl_execution import CrawlExecutionError, execute_crawl

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


@router.post("/run", response_model=CrawlRunResponse)
def run_crawl(
    request: CrawlRunRequest,
    _token: str = _Token,
    session: Session = _Session,
):
    """Execute a public web crawl run for an approved source and recipe."""
    import uuid

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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CrawlRunResponse(
        crawl_run_id=str(result.crawl_run_id),
        status=result.status,
        raw_object_id=str(result.raw_object_id) if result.raw_object_id else None,
        error_message=result.error_message,
    )
