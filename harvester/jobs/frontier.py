"""Source frontier management — cursor tracking and rewind detection."""

from __future__ import annotations

import datetime
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import SourceFrontier

logger = logging.getLogger(__name__)


def update_frontier(
    session: Session,
    source_id: uuid.UUID,
    cursor_value: str | None = None,
    frontier_state: dict | None = None,
    items_seen: list[dict] | None = None,
) -> SourceFrontier:
    """Create or update the frontier record for a source.

    Parameters
    ----------
    session : Session
        Active database session.
    source_id : uuid.UUID
        The source whose frontier is being updated.
    cursor_value : str or None
        New cursor value (e.g. pagination token, timestamp).
    frontier_state : dict or None
        Arbitrary state blob persisted alongside the cursor.
    items_seen : list[dict] or None
        If provided, each entry should have a ``"cursor"`` key.  The function
        computes the ``min`` and ``max`` cursor values and stores them as
        ``last_complete_range``.

    Returns
    -------
    SourceFrontier
        The upserted frontier record.
    """
    frontier = session.scalar(
        sa.select(SourceFrontier).where(SourceFrontier.source_id == source_id)
    )

    now = datetime.datetime.now(datetime.UTC)

    if frontier is None:
        frontier = SourceFrontier(
            id=uuid.uuid4(),
            source_id=source_id,
            updated_at=now,
        )
        session.add(frontier)
        # Flush so that the instance is usable within this transaction.
        session.flush()

    if cursor_value is not None:
        frontier.cursor_value = cursor_value

    if frontier_state is not None:
        frontier.frontier_state = frontier_state

    if items_seen:
        cursors = [item["cursor"] for item in items_seen if "cursor" in item]
        if cursors:
            # Attempt numeric comparison for sorting; fall back to string sort.
            try:
                sorted_cursors = sorted(cursors, key=lambda c: float(c))
            except (ValueError, TypeError):
                sorted_cursors = sorted(cursors)
            frontier.last_complete_range = {
                "min": sorted_cursors[0],
                "max": sorted_cursors[-1],
            }

    frontier.updated_at = now
    session.commit()
    return frontier


def should_rewind(
    session: Session,
    source_id: uuid.UUID,
    item_cursor: str,
) -> bool:
    """Check whether *item_cursor* falls within the rewind window.

    An item should be rewound (re-processed) when its cursor is older than the
    current frontier cursor but still within the rewind window range stored in
    ``last_complete_range``.

    Parameters
    ----------
    session : Session
        Active database session.
    source_id : uuid.UUID
        The source to check.
    item_cursor : str
        The cursor value of the incoming item.

    Returns
    -------
    bool
        ``True`` if the item should be re-processed (it is within the rewind
        window), ``False`` otherwise.
    """
    frontier = session.scalar(
        sa.select(SourceFrontier).where(SourceFrontier.source_id == source_id)
    )
    if frontier is None:
        return False

    # No cursor set yet — nothing to rewind from.
    if frontier.cursor_value is None:
        return False

    # No rewind window configured — rewind is disabled.
    if frontier.rewind_window is None or frontier.rewind_window <= 0:
        return False

    # No known range — cannot determine rewind eligibility.
    if not frontier.last_complete_range:
        return False

    range_min = frontier.last_complete_range.get("min")
    range_max = frontier.last_complete_range.get("max")
    if range_min is None or range_max is None:
        return False

    # Try numeric comparison first; fall back to lexicographic.
    try:
        cursor_num = float(item_cursor)
        min_num = float(range_min)
        max_num = float(range_max)
        current_num = float(frontier.cursor_value)
        # Item is older than current cursor but within the known range.
        return (
            min_num <= cursor_num < current_num <= max_num
            or min_num <= cursor_num <= max_num < current_num
        )
    except (ValueError, TypeError):
        # Lexicographic comparison
        return (
            range_min <= item_cursor <= range_max
            and item_cursor < frontier.cursor_value
        )
