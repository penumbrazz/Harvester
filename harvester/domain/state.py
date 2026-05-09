"""State transition validation and execution for Harvester entities.

Each entity type defines a mapping of ``current_status -> [allowed_next_statuses]``.
Transition helpers validate the change, update the entity, and write an audit event.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from harvester.domain.audit import write_audit

# ---------------------------------------------------------------------------
# Transition maps — define legal status transitions per entity type
# ---------------------------------------------------------------------------

SOURCE_TRANSITIONS: dict[str, list[str]] = {
    "candidate": ["testing", "archived"],
    "testing": ["watched", "archived"],
    "watched": ["paused", "archived"],
    "paused": ["watched", "archived"],
    "archived": [],
}

TOPIC_TRANSITIONS: dict[str, list[str]] = {
    "active": ["paused", "expired", "archived"],
    "paused": ["active", "archived"],
    "expired": ["active", "archived"],
    "archived": [],
}

RECIPE_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["approved", "rejected"],
    "approved": ["deprecated"],
    "rejected": ["pending"],
    "deprecated": [],
}

CRAWL_RUN_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["running", "failed"],
    "running": ["completed", "failed"],
    "completed": [],
    "failed": ["pending"],
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_transition(
    transitions: dict[str, list[str]],
    current: str,
    target: str,
) -> bool:
    """Return ``True`` if *current* -> *target* is a legal transition.

    Parameters
    ----------
    transitions : dict
        The transition map to consult.
    current : str
        The entity's current status value.
    target : str
        The desired next status value.

    Returns
    -------
    bool
        ``True`` if the transition is allowed, ``False`` otherwise.
    """
    allowed = transitions.get(current, [])
    return target in allowed


# ---------------------------------------------------------------------------
# Transition execution
# ---------------------------------------------------------------------------


def transition_entity(
    session: Session,
    entity: Any,
    transitions: dict[str, list[str]],
    target_status: str,
    actor: str,
    entity_type: str,
    *,
    reason: str | None = None,
    status_attr: str = "status",
) -> None:
    """Validate and apply a state transition on *entity*.

    On success the entity's status attribute is updated and an audit
    event is written.  On failure the entity is **not** modified, an audit
    event recording the rejected attempt is written, and a :class:`ValueError`
    is raised.

    Parameters
    ----------
    session : Session
        Active database session (same transaction used for the update and
        the audit event).
    entity : Any
        An ORM object that has a status attribute (string).
    transitions : dict
        The transition map to validate against.
    target_status : str
        The desired new status value.
    actor : str
        Who or what is performing the transition.
    entity_type : str
        Human-readable entity type name for audit logging (e.g. ``"source"``).
    reason : str or None
        Optional reason for the transition.
    status_attr : str
        Name of the attribute holding the status value on *entity*.
        Defaults to ``"status"``; set to ``"approval_status"`` for Recipe.

    Raises
    ------
    ValueError
        If the transition is not legal according to *transitions*.
    """
    entity_id: uuid.UUID | None = getattr(entity, "id", None)
    current_status: str = getattr(entity, status_attr)

    if validate_transition(transitions, current_status, target_status):
        setattr(entity, status_attr, target_status)
        write_audit(
            session,
            actor=actor,
            action="status_change",
            entity_type=entity_type,
            entity_id=entity_id,
            before_state={"status": current_status},
            after_state={"status": target_status},
            reason=reason,
        )
    else:
        write_audit(
            session,
            actor=actor,
            action="status_change_rejected",
            entity_type=entity_type,
            entity_id=entity_id,
            before_state={"status": current_status},
            after_state={"status": target_status},
            reason=reason,
        )
        raise ValueError(
            f"Illegal {entity_type} status transition: "
            f"{current_status!r} -> {target_status!r}"
        )
