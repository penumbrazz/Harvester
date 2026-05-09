"""Dedup group collapse for search results.

Reduces a list of item version IDs so that each dedup group is
represented only by its canonical version.  Versions without a dedup
group pass through unchanged.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from harvester.db.models import DedupGroup, ItemVersion


def collapse_dedup_groups(
    session: Session,
    version_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Collapse dedup groups in the given version list.

    For each dedup group found among the input versions, only the
    ``canonical_item_version_id`` is kept.  Versions that do not belong
    to any dedup group are returned as-is.

    Args:
        session: SQLAlchemy ORM session.
        version_ids: List of item version IDs to collapse.

    Returns:
        Deduplicated list of version IDs (order preserved from input
        where possible).
    """
    if not version_ids:
        return []

    # Fetch versions with their dedup group info
    rows = (
        session.execute(
            sa.select(
                ItemVersion.id,
                ItemVersion.dedup_group_id,
            )
            .where(ItemVersion.id.in_(version_ids))
        )
        .fetchall()
    )

    # Map version_id -> dedup_group_id (or None)
    version_to_group: dict[uuid.UUID, uuid.UUID | None] = {
        row.id: row.dedup_group_id for row in rows
    }

    # Collect all dedup_group_ids that are present
    group_ids = {gid for gid in version_to_group.values() if gid is not None}

    # Map dedup_group_id -> canonical_version_id
    group_to_canonical: dict[uuid.UUID, uuid.UUID] = {}
    if group_ids:
        canon_rows = (
            session.execute(
                sa.select(
                    DedupGroup.id,
                    DedupGroup.canonical_item_version_id,
                )
                .where(DedupGroup.id.in_(group_ids))
            )
            .fetchall()
        )
        group_to_canonical = {
            row.id: row.canonical_item_version_id for row in canon_rows
        }

    # Build result preserving input order
    result: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()

    for vid in version_ids:
        gid = version_to_group.get(vid)
        if gid is None:
            # No dedup group: keep as-is
            representative = vid
        else:
            # Use canonical version for this group
            representative = group_to_canonical.get(gid, vid)

        if representative not in seen:
            seen.add(representative)
            result.append(representative)

    return result
