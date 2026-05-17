"""Tests for source frontier update and rewind logic."""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from harvester.jobs.frontier import should_rewind, update_frontier


def _insert_source(db_session, **overrides):
    """Helper to insert a source directly."""
    source_id = overrides.pop("id", uuid.uuid4())
    defaults = dict(
        id=source_id,
        name=f"test-source-{source_id.hex[:8]}",
        kind="rss",
        status="active",
        trust_level="medium",
        auth_required=False,
        failure_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    db_session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, "
            "created_at, updated_at) "
            "VALUES "
            "(:id, :name, :kind, :status, :trust_level, :auth_required, :failure_count, "
            ":created_at, :updated_at)"
        ),
        defaults,
    )
    return source_id


class TestUpdateFrontier:
    """Tests for the update_frontier function."""

    def test_creates_frontier_for_new_source(self, db_session):
        """Should create a frontier record when none exists."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        frontier = update_frontier(db_session, source_id, cursor_value="100")
        assert frontier is not None
        assert frontier.source_id == source_id
        assert frontier.cursor_value == "100"

    def test_updates_existing_frontier_cursor(self, db_session):
        """Should update the cursor on an existing frontier."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        f1 = update_frontier(db_session, source_id, cursor_value="100")
        f2 = update_frontier(db_session, source_id, cursor_value="200")

        assert f2.cursor_value == "200"
        assert f2.id == f1.id

    def test_stores_frontier_state(self, db_session):
        """Should persist arbitrary state alongside the cursor."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        state = {"page": 3, "has_more": True}
        frontier = update_frontier(
            db_session,
            source_id,
            cursor_value="50",
            frontier_state=state,
        )
        assert frontier.frontier_state == state

    def test_computes_last_complete_range_from_items_seen(self, db_session):
        """Should compute min/max range from items_seen list."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        items = [
            {"cursor": "10", "id": "a"},
            {"cursor": "20", "id": "b"},
            {"cursor": "30", "id": "c"},
        ]
        frontier = update_frontier(
            db_session,
            source_id,
            cursor_value="30",
            items_seen=items,
        )
        assert frontier.last_complete_range == {"min": "10", "max": "30"}

    def test_handles_string_cursors_lexicographically(self, db_session):
        """Should sort string cursors lexicographically when not numeric."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        items = [
            {"cursor": "c_cursor"},
            {"cursor": "a_cursor"},
            {"cursor": "b_cursor"},
        ]
        frontier = update_frontier(
            db_session,
            source_id,
            cursor_value="d_cursor",
            items_seen=items,
        )
        assert frontier.last_complete_range == {
            "min": "a_cursor",
            "max": "c_cursor",
        }


class TestShouldRewind:
    """Tests for the should_rewind function."""

    def test_no_frontier_returns_false(self, db_session):
        """Should return False when no frontier exists for the source."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        assert should_rewind(db_session, source_id, "10") is False

    def test_no_cursor_returns_false(self, db_session):
        """Should return False when the frontier has no cursor set."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        # Create frontier without cursor
        update_frontier(db_session, source_id)

        assert should_rewind(db_session, source_id, "10") is False

    def test_no_rewind_window_returns_false(self, db_session):
        """Should return False when rewind_window is not configured."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        update_frontier(db_session, source_id, cursor_value="100")
        assert should_rewind(db_session, source_id, "50") is False

    def test_item_within_rewind_window_returns_true(self, db_session):
        """Should return True for items within the rewind window."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        # Set up frontier with cursor at 100 and range [10..100]
        items = [{"cursor": str(i)} for i in range(10, 101, 10)]
        frontier = update_frontier(
            db_session,
            source_id,
            cursor_value="100",
            items_seen=items,
        )
        # Enable rewind window
        frontier.rewind_window = 100
        db_session.commit()

        # Item at cursor 50 is within range and behind current cursor
        assert should_rewind(db_session, source_id, "50") is True

    def test_item_ahead_of_cursor_returns_false(self, db_session):
        """Should return False for items ahead of the current cursor."""
        source_id = _insert_source(db_session, id=uuid.uuid4())
        db_session.commit()

        items = [{"cursor": str(i)} for i in range(10, 101, 10)]
        frontier = update_frontier(
            db_session,
            source_id,
            cursor_value="50",
            items_seen=items,
        )
        frontier.rewind_window = 100
        db_session.commit()

        # Item at 200 is ahead of cursor, not in range
        assert should_rewind(db_session, source_id, "200") is False
