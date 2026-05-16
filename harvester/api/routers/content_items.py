"""Content item list API endpoint for browsing the content library."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.api.schemas import PaginatedResponse
from harvester.db.models import ContentItem, Source

router = APIRouter(prefix="/items", tags=["content"])


class ContentItemResponse(BaseModel):
    """Content item summary for library listing."""

    id: str
    item_type: str
    source_id: str | None = None
    source_name: str | None = None
    topic_watch_id: str | None = None
    title: str | None = None
    canonical_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ContentListResponse(PaginatedResponse[ContentItemResponse]):
    """Paginated content item list response."""


_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


@router.get("/content", response_model=ContentListResponse)
def list_content_items(
    source_id: Optional[UUID] = Query(None, description="Filter by source"),
    topic_watch_id: Optional[UUID] = Query(None, description="Filter by topic watch"),
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _token: str = _Token,
    session: Session = _Session,
):
    """List content items with pagination, filtering and stable sorting.

    Returns items sorted by updated_at descending (most recently updated first).
    Joins with sources table to include source_name for display.
    """
    # Base query with source name join
    query = session.query(ContentItem, Source.name.label("source_name")).outerjoin(
        Source, ContentItem.source_id == Source.id
    )

    # Apply filters
    if source_id is not None:
        query = query.filter(ContentItem.source_id == source_id)
    if topic_watch_id is not None:
        query = query.filter(ContentItem.topic_watch_id == topic_watch_id)
    if item_type is not None:
        query = query.filter(ContentItem.item_type == item_type)
    if status is not None:
        query = query.filter(ContentItem.status == status)

    # Total count before pagination
    count_query = query.with_entities(func.count(ContentItem.id))
    total = count_query.scalar() or 0

    # Apply sorting and pagination
    query = query.order_by(ContentItem.updated_at.desc()).limit(limit).offset(offset)

    rows = query.all()

    items = [
        ContentItemResponse(
            id=str(row.ContentItem.id),
            item_type=row.ContentItem.item_type,
            source_id=str(row.ContentItem.source_id)
            if row.ContentItem.source_id
            else None,
            source_name=row.source_name,
            topic_watch_id=(
                str(row.ContentItem.topic_watch_id)
                if row.ContentItem.topic_watch_id
                else None
            ),
            title=row.ContentItem.title,
            canonical_url=row.ContentItem.canonical_url,
            status=row.ContentItem.status,
            created_at=row.ContentItem.created_at,
            updated_at=row.ContentItem.updated_at,
        )
        for row in rows
    ]

    return ContentListResponse(items=items, total=total, limit=limit, offset=offset)
