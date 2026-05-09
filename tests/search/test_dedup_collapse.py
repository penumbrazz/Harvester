"""Tests for dedup group collapse in search results.

These tests exercise the ``collapse_dedup_groups`` function which
reduces a list of item version IDs to one representative per dedup group.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from harvester.db.models import ContentItem, DedupGroup, ItemVersion, Source


def _make_source(session: Session, name: str = "test_source") -> Source:
    """Create and persist a Source row."""
    src = Source(name=name, kind="rss")
    session.add(src)
    session.flush()
    return src


def _make_item(session: Session, title: str, source_id: uuid.UUID) -> ContentItem:
    """Create and persist a ContentItem."""
    ci = ContentItem(item_type="article", title=title, source_id=source_id)
    session.add(ci)
    session.flush()
    return ci


def _make_version(
    session: Session,
    content_item_id: uuid.UUID,
    dedup_group_id: uuid.UUID | None = None,
) -> ItemVersion:
    """Create and persist an ItemVersion."""
    iv = ItemVersion(
        content_item_id=content_item_id,
        content_hash=uuid.uuid4().hex,
        dedup_group_id=dedup_group_id,
    )
    session.add(iv)
    session.flush()
    return iv


def _make_dedup_group(
    session: Session,
    canonical_version_id: uuid.UUID | None = None,
) -> DedupGroup:
    """Create and persist a DedupGroup."""
    dg = DedupGroup(canonical_item_version_id=canonical_version_id)
    session.add(dg)
    session.flush()
    return dg


class TestDedupCollapse:
    """Tests for the collapse_dedup_groups function."""

    def test_items_without_dedup_group_returned_as_is(self, db_session):
        """Items without a dedup_group_id are returned unchanged."""
        from harvester.search.dedup import collapse_dedup_groups

        src = _make_source(db_session)
        ci = _make_item(db_session, "No Dedup", src.id)
        iv = _make_version(db_session, ci.id)

        result = collapse_dedup_groups(db_session, [iv.id])
        assert result == [iv.id]

    def test_dedup_group_returns_only_canonical(self, db_session):
        """When two versions share a dedup_group_id, only the canonical is kept."""
        from harvester.search.dedup import collapse_dedup_groups

        src = _make_source(db_session)
        ci_a = _make_item(db_session, "Article A", src.id)
        ci_b = _make_item(db_session, "Article B (dup)", src.id)
        iv_a = _make_version(db_session, ci_a.id)
        iv_b = _make_version(db_session, ci_b.id)

        # Create dedup group with iv_a as canonical
        dg = _make_dedup_group(db_session, canonical_version_id=iv_a.id)
        # Assign both versions to the same dedup group
        iv_a.dedup_group_id = dg.id
        iv_b.dedup_group_id = dg.id
        db_session.flush()

        result = collapse_dedup_groups(db_session, [iv_a.id, iv_b.id])
        assert result == [iv_a.id]

    def test_mixed_dedup_and_non_dedup(self, db_session):
        """Items with and without dedup groups are handled together."""
        from harvester.search.dedup import collapse_dedup_groups

        src = _make_source(db_session)
        ci_a = _make_item(db_session, "Dedup A", src.id)
        ci_b = _make_item(db_session, "Dedup B", src.id)
        ci_c = _make_item(db_session, "No Dedup C", src.id)
        iv_a = _make_version(db_session, ci_a.id)
        iv_b = _make_version(db_session, ci_b.id)
        iv_c = _make_version(db_session, ci_c.id)

        dg = _make_dedup_group(db_session, canonical_version_id=iv_a.id)
        iv_a.dedup_group_id = dg.id
        iv_b.dedup_group_id = dg.id
        db_session.flush()

        result = collapse_dedup_groups(db_session, [iv_a.id, iv_b.id, iv_c.id])
        # iv_b should be collapsed to iv_a; iv_c kept as-is
        assert iv_a.id in result
        assert iv_c.id in result
        assert iv_b.id not in result
        assert len(result) == 2

    def test_empty_input_returns_empty(self, db_session):
        """Empty input list returns empty output."""
        from harvester.search.dedup import collapse_dedup_groups

        result = collapse_dedup_groups(db_session, [])
        assert result == []

    def test_multiple_dedup_groups(self, db_session):
        """Multiple distinct dedup groups are collapsed independently."""
        from harvester.search.dedup import collapse_dedup_groups

        src = _make_source(db_session)
        ci_a = _make_item(db_session, "Group 1 A", src.id)
        ci_b = _make_item(db_session, "Group 1 B", src.id)
        ci_c = _make_item(db_session, "Group 2 C", src.id)
        ci_d = _make_item(db_session, "Group 2 D", src.id)

        iv_a = _make_version(db_session, ci_a.id)
        iv_b = _make_version(db_session, ci_b.id)
        iv_c = _make_version(db_session, ci_c.id)
        iv_d = _make_version(db_session, ci_d.id)

        dg1 = _make_dedup_group(db_session, canonical_version_id=iv_a.id)
        dg2 = _make_dedup_group(db_session, canonical_version_id=iv_c.id)

        iv_a.dedup_group_id = dg1.id
        iv_b.dedup_group_id = dg1.id
        iv_c.dedup_group_id = dg2.id
        iv_d.dedup_group_id = dg2.id
        db_session.flush()

        result = collapse_dedup_groups(
            db_session, [iv_a.id, iv_b.id, iv_c.id, iv_d.id]
        )
        assert set(result) == {iv_a.id, iv_c.id}
        assert len(result) == 2
