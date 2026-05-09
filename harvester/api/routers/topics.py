"""Topic API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import Source, TopicSource, TopicWatch
from harvester.domain.audit import write_audit

router = APIRouter(prefix="/topics", tags=["topics"])


class TopicCreateRequest(BaseModel):
    name: str
    query: str | None = None
    ttl_seconds: int | None = None


class TopicResponse(BaseModel):
    id: str
    name: str
    status: str
    query: str | None
    ttl_seconds: int | None
    created_at: datetime


class TopicAttachSourceRequest(BaseModel):
    source_id: str


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    req: TopicCreateRequest,
    _token: str = Depends(require_api_token),
    session: Session = Depends(get_db_session),
):
    """Create a new topic watch."""
    expires_at = None
    if req.ttl_seconds:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=req.ttl_seconds)

    topic = TopicWatch(
        id=uuid.uuid4(),
        name=req.name,
        query=req.query,
        status="active",
        ttl_seconds=req.ttl_seconds,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(topic)
    write_audit(
        session,
        actor="api",
        action="topic.create",
        entity_type="topic_watch",
        entity_id=topic.id,
        after_state={"name": req.name, "status": "active"},
    )
    session.commit()
    session.refresh(topic)
    return TopicResponse(
        id=str(topic.id),
        name=topic.name,
        status=topic.status,
        query=topic.query,
        ttl_seconds=topic.ttl_seconds,
        created_at=topic.created_at,
    )


@router.post("/{topic_id}/sources", status_code=status.HTTP_201_CREATED)
def attach_source_to_topic(
    topic_id: str,
    req: TopicAttachSourceRequest,
    _token: str = Depends(require_api_token),
    session: Session = Depends(get_db_session),
):
    """Attach an existing source to a topic watch."""
    topic = session.get(TopicWatch, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    source = session.get(Source, req.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    existing = (
        session.query(TopicSource)
        .filter(
            TopicSource.topic_watch_id == topic.id,
            TopicSource.source_id == source.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Source already attached to this topic")

    link = TopicSource(
        id=uuid.uuid4(),
        topic_watch_id=topic.id,
        source_id=source.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(link)
    write_audit(
        session,
        actor="api",
        action="topic.attach_source",
        entity_type="topic_watch",
        entity_id=topic.id,
        after_state={"source_id": str(source.id)},
    )
    session.commit()
    return {"status": "attached", "topic_id": topic_id, "source_id": req.source_id}
