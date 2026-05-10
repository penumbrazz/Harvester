"""Watch schedule API endpoints — create and manage crawl schedules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import Recipe, Source, TopicWatch, WatchSchedule
from harvester.domain.audit import write_audit

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreateRequest(BaseModel):
    source_id: str
    topic_watch_id: str | None = None
    recipe_id: str
    interval_seconds: int
    priority: int = 0
    lane: str | None = None


class ScheduleResponse(BaseModel):
    id: str
    schedule_key: str
    source_id: str
    topic_watch_id: str | None
    recipe_id: str
    status: str
    interval_seconds: int
    next_run_at: datetime
    last_enqueued_at: datetime | None
    priority: int
    lane: str | None
    created_at: datetime


def _build_schedule_key(
    source_id: uuid.UUID,
    recipe_id: uuid.UUID,
    topic_watch_id: uuid.UUID | None,
) -> str:
    """Generate a stable unique key for the schedule."""
    if topic_watch_id:
        return f"topic:{topic_watch_id}:source:{source_id}:recipe:{recipe_id}"
    return f"source:{source_id}:recipe:{recipe_id}"


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    req: ScheduleCreateRequest,
    _token: str = Depends(require_api_token),
    session: Session = Depends(get_db_session),
):
    """Create a new watch schedule."""
    # Parse and validate source
    try:
        source_uuid = uuid.UUID(req.source_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid source_id format")

    source = session.get(Source, source_uuid)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.status not in ("watched", "active"):
        raise HTTPException(
            status_code=422,
            detail=f"Source status '{source.status}' is not schedulable",
        )

    # Parse and validate recipe
    try:
        recipe_uuid = uuid.UUID(req.recipe_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid recipe_id format")

    recipe = session.get(Recipe, recipe_uuid)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.approval_status != "approved":
        raise HTTPException(
            status_code=422,
            detail=f"Recipe approval_status is '{recipe.approval_status}', must be 'approved'",
        )

    # Parse and validate topic_watch (optional)
    topic_uuid: uuid.UUID | None = None
    if req.topic_watch_id:
        try:
            topic_uuid = uuid.UUID(req.topic_watch_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid topic_watch_id format")

        topic = session.get(TopicWatch, topic_uuid)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic watch not found")
        if topic.status != "active":
            raise HTTPException(
                status_code=422,
                detail=f"Topic watch status is '{topic.status}', must be 'active'",
            )

    # Build schedule_key and check duplicates
    schedule_key = _build_schedule_key(source_uuid, recipe_uuid, topic_uuid)
    existing = (
        session.query(WatchSchedule)
        .filter(WatchSchedule.schedule_key == schedule_key)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Schedule already exists with key '{schedule_key}'",
        )

    # Validate interval
    if req.interval_seconds < 60:
        raise HTTPException(
            status_code=422,
            detail="interval_seconds must be at least 60",
        )

    now = datetime.now(timezone.utc)
    schedule = WatchSchedule(
        id=uuid.uuid4(),
        schedule_key=schedule_key,
        source_id=source_uuid,
        topic_watch_id=topic_uuid,
        recipe_id=recipe_uuid,
        status="active",
        interval_seconds=req.interval_seconds,
        next_run_at=now,
        priority=req.priority,
        lane=req.lane,
        created_at=now,
        updated_at=now,
    )
    session.add(schedule)

    write_audit(
        session,
        actor="api",
        action="schedule.create",
        entity_type="watch_schedule",
        entity_id=schedule.id,
        after_state={
            "schedule_key": schedule_key,
            "source_id": str(source_uuid),
            "recipe_id": str(recipe_uuid),
            "interval_seconds": req.interval_seconds,
        },
    )

    session.commit()
    session.refresh(schedule)

    return ScheduleResponse(
        id=str(schedule.id),
        schedule_key=schedule.schedule_key,
        source_id=str(schedule.source_id),
        topic_watch_id=str(schedule.topic_watch_id) if schedule.topic_watch_id else None,
        recipe_id=str(schedule.recipe_id),
        status=schedule.status,
        interval_seconds=schedule.interval_seconds,
        next_run_at=schedule.next_run_at,
        last_enqueued_at=schedule.last_enqueued_at,
        priority=schedule.priority,
        lane=schedule.lane,
        created_at=schedule.created_at,
    )
