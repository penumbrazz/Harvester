"""Source API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import Source
from harvester.domain.audit import write_audit
from harvester.domain.state import SOURCE_TRANSITIONS, transition_entity

router = APIRouter(prefix="/sources", tags=["sources"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class SourceProposeRequest(BaseModel):
    name: str
    kind: str
    url: str | None = None
    trust_level: str = "medium"
    auth_required: bool = False


class SourceResponse(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    url: str | None
    trust_level: str
    failure_count: int
    created_at: datetime
    updated_at: datetime


class SourcePromoteRequest(BaseModel):
    reason: str | None = None


def _source_to_response(source: Source) -> SourceResponse:
    """Serialize a Source ORM instance to SourceResponse."""
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        kind=source.kind,
        status=source.status,
        url=source.url,
        trust_level=source.trust_level,
        failure_count=source.failure_count,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.get("", response_model=list[SourceResponse])
def list_sources(
    status_filter: Optional[str] = Query(None, alias="status"),
    kind_filter: Optional[str] = Query(None, alias="kind"),
    _token: str = _Token,
    session: Session = _Session,
):
    """List all sources, optionally filtered by status and/or kind.

    Returns sources sorted by created_at descending (newest first).
    """
    query = session.query(Source)

    if status_filter is not None:
        query = query.filter(Source.status == status_filter)
    if kind_filter is not None:
        query = query.filter(Source.kind == kind_filter)

    sources = query.order_by(Source.created_at.desc()).all()
    return [_source_to_response(s) for s in sources]


@router.post("/propose", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def propose_source(
    req: SourceProposeRequest,
    _token: str = _Token,
    session: Session = _Session,
):
    """Propose a new candidate source."""
    existing = session.query(Source).filter(Source.name == req.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Source '{req.name}' already exists")

    source = Source(
        id=uuid.uuid4(),
        name=req.name,
        kind=req.kind,
        url=req.url,
        status="candidate",
        trust_level=req.trust_level,
        auth_required=req.auth_required,
        failure_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(source)
    write_audit(
        session,
        actor="api",
        action="source.propose",
        entity_type="source",
        entity_id=source.id,
        after_state={"name": req.name, "kind": req.kind, "status": "candidate"},
    )
    session.commit()
    session.refresh(source)
    return _source_to_response(source)


def _resolve_source(source_id: str, session: Session) -> Source:
    """Parse source_id to UUID and fetch the Source, or raise 404/422."""
    try:
        parsed_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid source_id format") from None
    source = session.get(Source, parsed_uuid)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/promote", response_model=SourceResponse)
def promote_source(
    source_id: str,
    body: SourcePromoteRequest | None = None,
    _token: str = _Token,
    session: Session = _Session,
):
    """Promote a candidate source to testing, or testing to watched."""
    source = _resolve_source(source_id, session)

    # Determine next status based on current
    current = source.status
    if current == "candidate":
        target = "testing"
    elif current == "testing":
        target = "watched"
    else:
        raise HTTPException(status_code=400, detail=f"Cannot promote source in '{current}' status")

    reason = body.reason if body else None
    try:
        transition_entity(session, source, SOURCE_TRANSITIONS, target, "api", "source", reason=reason)
    except ValueError as e:
        # Commit to persist the rejection audit written by transition_entity.
        session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(source)
    return _source_to_response(source)


@router.post("/{source_id}/pause", response_model=SourceResponse)
def pause_source(
    source_id: str,
    _token: str = _Token,
    session: Session = _Session,
):
    """Pause a watched source."""
    source = _resolve_source(source_id, session)

    try:
        transition_entity(session, source, SOURCE_TRANSITIONS, "paused", "api", "source")
    except ValueError as e:
        session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(source)
    return _source_to_response(source)


@router.post("/{source_id}/resume", response_model=SourceResponse)
def resume_source(
    source_id: str,
    _token: str = _Token,
    session: Session = _Session,
):
    """Resume a paused source back to watched."""
    source = _resolve_source(source_id, session)

    try:
        transition_entity(session, source, SOURCE_TRANSITIONS, "watched", "api", "source")
    except ValueError as e:
        session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(source)
    return _source_to_response(source)


@router.post("/{source_id}/archive", response_model=SourceResponse)
def archive_source(
    source_id: str,
    _token: str = _Token,
    session: Session = _Session,
):
    """Archive a source (terminal state)."""
    source = _resolve_source(source_id, session)

    try:
        transition_entity(session, source, SOURCE_TRANSITIONS, "archived", "api", "source")
    except ValueError as e:
        session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(source)
    return _source_to_response(source)
