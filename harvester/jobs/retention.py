"""Raw payload retention management — marking extracted objects and cleanup."""

from __future__ import annotations

import datetime
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import RawObject

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 7


def mark_raw_object_extracted(
    session: Session,
    raw_object_id: uuid.UUID,
) -> None:
    """Mark a raw object as successfully extracted with a retention deadline.

    Sets ``retention_policy`` to ``"extracted"`` and ``retain_until`` to
    ``now + DEFAULT_RETENTION_DAYS``.

    Parameters
    ----------
    session : Session
        Active database session.
    raw_object_id : uuid.UUID
        The raw object to mark.
    """
    raw_obj = session.get(RawObject, raw_object_id)
    if raw_obj is None:
        raise ValueError(f"RawObject {raw_object_id} not found")

    now = datetime.datetime.now(datetime.UTC)
    raw_obj.retention_policy = "extracted"
    raw_obj.retain_until = now + datetime.timedelta(days=DEFAULT_RETENTION_DAYS)

    session.commit()
    logger.info(
        "Raw object %s marked as extracted, retain_until=%s",
        raw_object_id,
        raw_obj.retain_until.isoformat(),
    )


def cleanup_expired_payloads(
    session: Session,
    archive_path: str | None = None,
) -> list[RawObject]:
    """Find raw objects whose retention deadline has passed.

    This function queries for expired raw objects and logs them for external
    cleanup (e.g. by a CLI tool).  It does **not** delete files or remove
    database rows — the caller is responsible for actual deletion.

    Parameters
    ----------
    session : Session
        Active database session.
    archive_path : str or None
        Optional base directory where payloads are archived before deletion.
        Currently used only for logging context.

    Returns
    -------
    list[RawObject]
        Raw objects whose ``retain_until`` is in the past.
    """
    now = datetime.datetime.now(datetime.UTC)

    expired = list(
        session.scalars(
            sa.select(RawObject).where(
                RawObject.retain_until.isnot(None),
                RawObject.retain_until < now,
            )
        ).all()
    )

    for raw_obj in expired:
        retain_str = raw_obj.retain_until.isoformat() if raw_obj.retain_until else "N/A"
        logger.info(
            "Raw object %s expired (retain_until=%s, storage_uri=%s)%s",
            raw_obj.id,
            retain_str,
            raw_obj.storage_uri or "none",
            f" — archive_path={archive_path}" if archive_path else "",
        )

    logger.info("Found %d expired raw objects for cleanup", len(expired))
    return expired
