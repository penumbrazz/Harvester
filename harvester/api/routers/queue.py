"""Queue status API endpoint — aggregated job queue statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session

router = APIRouter(prefix="/queue", tags=["queue"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)


class QueueStatusItem(BaseModel):
    job_type: str
    status: str
    count: int


@router.get("/status", response_model=list[QueueStatusItem])
def get_queue_status(
    _token: str = _Token,
    session: Session = _Session,
):
    """Return job queue counts aggregated by job_type and status.

    Does NOT return raw payload data.
    """
    rows = session.execute(
        text(
            "SELECT job_type, status, COUNT(*) as cnt "
            "FROM jobs "
            "GROUP BY job_type, status "
            "ORDER BY job_type, status"
        )
    ).fetchall()
    return [
        QueueStatusItem(job_type=row[0], status=row[1], count=row[2])
        for row in rows
    ]
