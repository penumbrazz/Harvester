"""Content item list API endpoint for browsing the content library."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.api.schemas import PaginatedResponse
from harvester.db.models import ContentItem, ItemVersion, Source

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


class ItemVersionResponse(BaseModel):
    """Item version summary for detail view."""

    id: str
    normalized_text: str | None = None
    language: str | None = None
    content_hash: str
    created_at: datetime


class ContentDetailResponse(BaseModel):
    """Full content item detail with latest version."""

    id: str
    item_type: str
    title: str | None = None
    canonical_url: str | None = None
    status: str
    source_name: str | None = None
    created_at: datetime
    updated_at: datetime
    latest_version: ItemVersionResponse | None = None


_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


@router.get("/content/{content_item_id}", response_model=ContentDetailResponse)
def get_content_item_detail(
    content_item_id: UUID,
    _token: str = _Token,
    session: Session = _Session,
):
    """Get a single content item with its latest version text."""
    row = (
        session.query(ContentItem, Source.name.label("source_name"))
        .outerjoin(Source, ContentItem.source_id == Source.id)
        .filter(ContentItem.id == content_item_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Content item not found")

    content_item = row.ContentItem
    source_name = row.source_name

    latest_version = (
        session.query(ItemVersion)
        .filter(ItemVersion.content_item_id == content_item_id)
        .order_by(ItemVersion.created_at.desc())
        .first()
    )

    return ContentDetailResponse(
        id=str(content_item.id),
        item_type=content_item.item_type,
        title=content_item.title,
        canonical_url=content_item.canonical_url,
        status=content_item.status,
        source_name=source_name,
        created_at=content_item.created_at,
        updated_at=content_item.updated_at,
        latest_version=(
            ItemVersionResponse(
                id=str(latest_version.id),
                normalized_text=latest_version.normalized_text,
                language=latest_version.language,
                content_hash=latest_version.content_hash,
                created_at=latest_version.created_at,
            )
            if latest_version
            else None
        ),
    )


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
