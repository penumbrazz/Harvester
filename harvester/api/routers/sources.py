"""Source API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
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
    created_at: datetime


class SourcePromoteRequest(BaseModel):
    reason: str | None = None


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
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        kind=source.kind,
        status=source.status,
        url=source.url,
        trust_level=source.trust_level,
        created_at=source.created_at,
    )


@router.post("/{source_id}/promote", response_model=SourceResponse)
def promote_source(
    source_id: str,
    body: SourcePromoteRequest | None = None,
    _token: str = _Token,
    session: Session = _Session,
):
    """Promote a candidate source to testing, or testing to watched."""
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

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
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        kind=source.kind,
        status=source.status,
        url=source.url,
        trust_level=source.trust_level,
        created_at=source.created_at,
    )


@router.post("/{source_id}/pause", response_model=SourceResponse)
def pause_source(
    source_id: str,
    _token: str = _Token,
    session: Session = _Session,
):
    """Pause a watched source."""
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        transition_entity(session, source, SOURCE_TRANSITIONS, "paused", "api", "source")
    except ValueError as e:
        session.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(source)
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        kind=source.kind,
        status=source.status,
        url=source.url,
        trust_level=source.trust_level,
        created_at=source.created_at,
    )
