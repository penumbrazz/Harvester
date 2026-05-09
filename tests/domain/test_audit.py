"""Tests for harvester.domain.audit.write_audit."""

import uuid

import sqlalchemy as sa

from harvester.domain.audit import write_audit


def test_write_audit_creates_event(db_session):
    """write_audit should add an AuditEvent to the session."""
    # Arrange
    entity_id = uuid.uuid4()

    # Act
    event = write_audit(
        db_session,
        actor="test",
        action="test.action",
        entity_type="source",
        entity_id=entity_id,
        before_state={"status": "old"},
        after_state={"status": "new"},
        reason="testing",
    )
    db_session.commit()

    # Assert — verify the event was persisted
    result = db_session.execute(
        sa.text("SELECT actor, action, entity_type FROM audit_events WHERE id = :id"),
        {"id": str(event.id)},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "test"
    assert row[1] == "test.action"
    assert row[2] == "source"


def test_write_audit_persists_all_fields(db_session):
    """write_audit should persist entity_id, before/after state, and reason."""
    # Arrange
    entity_id = uuid.uuid4()

    # Act
    event = write_audit(
        db_session,
        actor="cli",
        action="source.delete",
        entity_type="source",
        entity_id=entity_id,
        before_state={"status": "active", "name": "old-source"},
        after_state={"status": "deleted"},
        reason="duplicate",
    )
    db_session.commit()

    # Assert
    result = db_session.execute(
        sa.text(
            "SELECT entity_id, before_state, after_state, reason "
            "FROM audit_events WHERE id = :id"
        ),
        {"id": str(event.id)},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == entity_id
    assert row[1]["status"] == "active"
    assert row[2]["status"] == "deleted"
    assert row[3] == "duplicate"


def test_write_audit_minimal_fields(db_session):
    """write_audit should work with only required fields (actor, action, entity_type)."""
    # Act
    event = write_audit(
        db_session,
        actor="system",
        action="heartbeat",
        entity_type="system",
    )
    db_session.commit()

    # Assert
    result = db_session.execute(
        sa.text("SELECT actor, action, entity_type, entity_id FROM audit_events WHERE id = :id"),
        {"id": str(event.id)},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "system"
    assert row[1] == "heartbeat"
    assert row[2] == "system"
    assert row[3] is None
