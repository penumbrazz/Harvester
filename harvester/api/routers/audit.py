"""Audit event query API endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)

# Maximum characters for state summary values
_SUMMARY_MAX_LEN = 200


def _summarize_state(state: dict | None) -> str | None:
    """Create a short human-readable summary of a state dict.

    Returns a truncated key=value string, or None if the state is empty.
    """
    if not state:
        return None
    parts = []
    for key, value in state.items():
        val_str = json.dumps(value, default=str) if not isinstance(value, str) else value
        if len(val_str) > _SUMMARY_MAX_LEN:
            val_str = val_str[: _SUMMARY_MAX_LEN - 3] + "..."
        parts.append(f"{key}={val_str}")
    result = ", ".join(parts)
    if len(result) > _SUMMARY_MAX_LEN:
        result = result[: _SUMMARY_MAX_LEN - 3] + "..."
    return result


class AuditEventItem(BaseModel):
    id: str
    actor: str | None
    action: str
    entity_type: str
    entity_id: str | None
    before_summary: str | None
    after_summary: str | None
    reason: str | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventItem]
    total: int


@router.get("/events", response_model=AuditEventListResponse)
def list_audit_events(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    time_from: Optional[datetime] = Query(None),
    time_to: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _token: str = _Token,
    session: Session = _Session,
):
    """List audit events with optional filters, sorted by created_at descending.

    Returns summarized before/after state instead of raw JSONB payloads.
    """
    query = session.query(AuditEvent)

    if entity_type is not None:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if action is not None:
        query = query.filter(AuditEvent.action == action)
    if actor is not None:
        query = query.filter(AuditEvent.actor == actor)
    if time_from is not None:
        query = query.filter(AuditEvent.created_at >= time_from)
    if time_to is not None:
        query = query.filter(AuditEvent.created_at <= time_to)

    total = query.count()
    events = query.order_by(desc(AuditEvent.created_at)).offset(offset).limit(limit).all()

    return AuditEventListResponse(
        items=[
            AuditEventItem(
                id=str(e.id),
                actor=e.actor,
                action=e.action,
                entity_type=e.entity_type,
                entity_id=str(e.entity_id) if e.entity_id else None,
                before_summary=_summarize_state(e.before_state),
                after_summary=_summarize_state(e.after_state),
                reason=e.reason,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
    )
