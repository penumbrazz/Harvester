"""Audit event writing helper for Harvester."""

import uuid
from datetime import UTC, datetime

from harvester.db.models import AuditEvent


def write_audit(
    session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    reason: str | None = None,
) -> AuditEvent:
    """Write an audit event in the current transaction.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        The database session to add the event to.
    actor : str
        Who or what triggered the event (e.g. user id, system service name).
    action : str
        What happened (e.g. ``"status_change"``, ``"create"``, ``"delete"``).
    entity_type : str
        The type of entity affected (e.g. ``"source"``, ``"recipe"``).
    entity_id : uuid.UUID or None
        Primary key of the affected entity.
    before_state : dict or None
        Snapshot of the entity state before the action.
    after_state : dict or None
        Snapshot of the entity state after the action.
    reason : str or None
        Optional human-readable explanation for the action.

    Returns
    -------
    AuditEvent
        The persisted audit event instance (not yet committed).
    """
    event = AuditEvent(
        id=uuid.uuid4(),
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    session.add(event)
    return event
