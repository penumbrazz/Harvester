"""Tests for harvester.domain.state transition validation and execution."""

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

from harvester.db.models import Source
from harvester.domain.state import (
    CRAWL_TARGET_TRANSITIONS,
    SOURCE_TRANSITIONS,
    validate_transition,
    transition_entity,
)


class TestValidateTransition:
    """Tests for validate_transition (pure function, no database)."""

    def test_valid_source_transition(self):
        """candidate -> testing should be a valid transition."""
        # Act
        result = validate_transition(SOURCE_TRANSITIONS, "candidate", "testing")

        # Assert
        assert result is True

    def test_invalid_source_transition(self):
        """candidate -> watched should NOT be a valid transition."""
        # Act
        result = validate_transition(SOURCE_TRANSITIONS, "candidate", "watched")

        # Assert
        assert result is False

    def test_archived_is_terminal(self):
        """archived should have no outgoing transitions."""
        # Act
        result = validate_transition(SOURCE_TRANSITIONS, "archived", "active")

        # Assert
        assert result is False

    def test_unknown_current_status(self):
        """An unknown current status should return False."""
        # Act
        result = validate_transition(SOURCE_TRANSITIONS, "nonexistent", "candidate")

        # Assert
        assert result is False

    def test_crawl_target_lifecycle_statuses(self):
        """Crawl targets should support the minimal execution lifecycle."""
        # Arrange
        expected_statuses = {"pending", "running", "completed", "failed", "skipped"}

        # Act
        actual_statuses = set(CRAWL_TARGET_TRANSITIONS)

        # Assert
        assert expected_statuses.issubset(actual_statuses)
        assert validate_transition(CRAWL_TARGET_TRANSITIONS, "pending", "running")
        assert validate_transition(CRAWL_TARGET_TRANSITIONS, "pending", "skipped")
        assert validate_transition(CRAWL_TARGET_TRANSITIONS, "running", "completed")
        assert validate_transition(CRAWL_TARGET_TRANSITIONS, "running", "failed")
        assert validate_transition(CRAWL_TARGET_TRANSITIONS, "failed", "pending")
        assert not validate_transition(CRAWL_TARGET_TRANSITIONS, "completed", "running")


class TestTransitionEntity:
    """Tests for transition_entity (requires database session)."""

    def test_valid_transition_updates_status(self, db_session):
        """transition_entity should update status on valid transition."""
        # Arrange
        source = Source(
            id=uuid.uuid4(),
            name=f"test-{uuid.uuid4().hex[:6]}",
            kind="web",
            status="candidate",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(source)
        db_session.commit()

        # Act
        transition_entity(
            db_session, source, SOURCE_TRANSITIONS, "testing", "test", "source"
        )
        db_session.commit()

        # Assert — status updated
        db_session.refresh(source)
        assert source.status == "testing"

        # Assert — audit event created
        result = db_session.execute(
            sa.text("SELECT action FROM audit_events WHERE entity_id = :eid"),
            {"eid": str(source.id)},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "status_change"

    def test_valid_transition_with_reason(self, db_session):
        """transition_entity should pass reason to the audit event."""
        # Arrange
        source = Source(
            id=uuid.uuid4(),
            name=f"test-{uuid.uuid4().hex[:6]}",
            kind="web",
            status="candidate",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(source)
        db_session.commit()

        # Act
        transition_entity(
            db_session,
            source,
            SOURCE_TRANSITIONS,
            "archived",
            "test",
            "source",
            reason="deprecated source",
        )
        db_session.commit()

        # Assert
        result = db_session.execute(
            sa.text("SELECT reason FROM audit_events WHERE entity_id = :eid"),
            {"eid": str(source.id)},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "deprecated source"

    def test_invalid_transition_raises(self, db_session):
        """transition_entity should raise ValueError on invalid transition."""
        # Arrange
        source = Source(
            id=uuid.uuid4(),
            name=f"test-{uuid.uuid4().hex[:6]}",
            kind="web",
            status="candidate",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(source)
        db_session.commit()

        # Act & Assert
        with pytest.raises(ValueError, match="Illegal"):
            transition_entity(
                db_session, source, SOURCE_TRANSITIONS, "watched", "test", "source"
            )

        # Assert — rollback and verify status unchanged
        db_session.rollback()
        db_session.refresh(source)
        assert source.status == "candidate"

    def test_invalid_transition_writes_rejection_audit(self, db_session):
        """transition_entity should write a rejection audit event on failure."""
        # Arrange
        source = Source(
            id=uuid.uuid4(),
            name=f"test-{uuid.uuid4().hex[:6]}",
            kind="web",
            status="candidate",
            trust_level="medium",
            auth_required=False,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(source)
        db_session.commit()

        # Act
        try:
            transition_entity(
                db_session, source, SOURCE_TRANSITIONS, "watched", "test", "source"
            )
        except ValueError:
            pass

        # Assert — rejection audit was committed via savepoint before ValueError
        result = db_session.execute(
            sa.text(
                "SELECT action FROM audit_events "
                "WHERE entity_id = :eid AND action = 'status_change_rejected'"
            ),
            {"eid": str(source.id)},
        )
        row = result.fetchone()
        assert row is not None, "Rejection audit event must be persisted"
        assert row[0] == "status_change_rejected"
