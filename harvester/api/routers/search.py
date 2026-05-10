"""Search API endpoint for keyword and vector content item retrieval."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.search.keyword import keyword_search

router = APIRouter(prefix="/items", tags=["search"])


class SearchMode(StrEnum):
    keyword = "keyword"
    vector = "vector"


class SearchItem(BaseModel):
    item_id: str | None = None
    version_id: str | None = None
    source_id: str | None = None
    title: str
    canonical_url: str | None = None
    created_at: datetime | None = None
    chunk_id: str | None = None
    item_version_id: str | None = None
    content_item_id: str | None = None
    text: str | None = None
    distance: float | None = None
    mode: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchItem]


_Q = Query(..., description="Search query keyword")
_Mode = Query("keyword", description="Search mode: keyword or vector")
_SourceId = Query(None, description="Filter by source")
_TopicWatchId = Query(None, description="Filter by topic watch")
_Limit = Query(20, ge=1, le=100, description="Max results")
_Offset = Query(0, ge=0, description="Pagination offset")
_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


@router.get("/search", response_model=SearchResponse)
def search_items(
    q: str = _Q,
    mode: SearchMode = _Mode,
    source_id: UUID | None = _SourceId,
    topic_watch_id: UUID | None = _TopicWatchId,
    limit: int = _Limit,
    offset: int = _Offset,
    _token: str = _Token,
    session: Session = _Session,
):
    """Search content items by keyword or vector similarity."""
    if not q.strip():
        return SearchResponse(items=[])

    if mode == SearchMode.vector:
        if offset > 0:
            raise HTTPException(
                status_code=422,
                detail="offset is not supported in vector mode",
            )
        return _vector_search(
            q, session, source_id=source_id, topic_watch_id=topic_watch_id, limit=limit
        )

    raw = keyword_search(
        session,
        q,
        source_id=source_id,
        topic_watch_id=topic_watch_id,
        limit=limit,
        offset=offset,
    )

    items = [
        SearchItem(
            item_id=str(row["item_id"]),
            version_id=str(row["version_id"]),
            source_id=str(row["source_id"]),
            title=row["title"],
            canonical_url=row["canonical_url"],
            created_at=row["created_at"],
            mode="keyword",
        )
        for row in raw
    ]
    return SearchResponse(items=items)


def _vector_search(
    q: str,
    session: Session,
    *,
    source_id: UUID | None = None,
    topic_watch_id: UUID | None = None,
    limit: int = 20,
) -> SearchResponse:
    from harvester.adapters.embedding_settings import create_embedding_adapter
    from harvester.search.vector import vector_search

    try:
        adapter, _model_name = create_embedding_adapter()
        query_embedding = adapter.embed(q)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding adapter unavailable: {exc}",
        ) from exc

    raw = vector_search(
        session,
        query_embedding,
        limit=limit,
        source_id=source_id,
        topic_watch_id=topic_watch_id,
    )

    items = [
        SearchItem(
            chunk_id=str(row["chunk_id"]),
            item_version_id=str(row["item_version_id"]),
            content_item_id=str(row["content_item_id"]),
            title=row["title"],
            text=row["text"],
            distance=row["distance"],
            mode="vector",
        )
        for row in raw
    ]
    return SearchResponse(items=items)
