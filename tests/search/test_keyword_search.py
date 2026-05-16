"""Tests for keyword search over content item titles.

These tests exercise the ``keyword_search`` function which uses ILIKE
on the title column of the latest item version per content item.
"""

import uuid

from sqlalchemy.orm import Session

from harvester.db.models import (
    ContentItem,
    DedupGroup,
    ItemVersion,
    Source,
    TopicWatch,
)


def _make_source(session: Session, name: str = "test_source") -> Source:
    """Create and persist a Source row."""
    src = Source(name=name, kind="rss")
    session.add(src)
    session.flush()
    return src


def _make_topic(session: Session, name: str = "test_topic") -> TopicWatch:
    """Create and persist a TopicWatch row."""
    tw = TopicWatch(name=name, query=name)
    session.add(tw)
    session.flush()
    return tw


def _make_item(
    session: Session,
    title: str,
    source_id: uuid.UUID | None = None,
    topic_watch_id: uuid.UUID | None = None,
) -> ContentItem:
    """Create and persist a ContentItem."""
    ci = ContentItem(
        item_type="article",
        title=title,
        source_id=source_id,
        topic_watch_id=topic_watch_id,
    )
    session.add(ci)
    session.flush()
    return ci


def _make_version(
    session: Session,
    content_item_id: uuid.UUID,
    normalized_text: str | None = None,
) -> ItemVersion:
    """Create and persist an ItemVersion."""
    iv = ItemVersion(
        content_item_id=content_item_id,
        content_hash=uuid.uuid4().hex,
        normalized_text=normalized_text,
    )
    session.add(iv)
    session.flush()
    return iv


class TestKeywordSearch:
    """Tests for the keyword_search function."""

    def test_search_by_keyword_returns_matching_items(self, db_session):
        """Search by keyword in title returns matching latest item versions."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Python Async Programming Guide", source_id=src.id)
        _make_version(db_session, ci.id, normalized_text="About async python")
        ci2 = _make_item(db_session, "Rust Ownership Model Explained", source_id=src.id)
        _make_version(db_session, ci2.id, normalized_text="About rust ownership")

        results = keyword_search(db_session, "Python")
        assert len(results) == 1
        assert results[0]["title"] == "Python Async Programming Guide"
        assert results[0]["item_id"] == ci.id

    def test_search_is_case_insensitive(self, db_session):
        """Keyword search should be case-insensitive."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Machine Learning Basics", source_id=src.id)
        _make_version(db_session, ci.id)

        results_lower = keyword_search(db_session, "machine")
        results_upper = keyword_search(db_session, "MACHINE")
        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert results_lower[0]["item_id"] == results_upper[0]["item_id"]

    def test_empty_query_returns_empty_results(self, db_session):
        """An empty query string should return no results."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Some Title", source_id=src.id)
        _make_version(db_session, ci.id)

        results = keyword_search(db_session, "")
        assert results == []

    def test_returns_latest_version_only(self, db_session):
        """Search should only return the latest version of each content item."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Web Scraping with Python", source_id=src.id)
        # Create an older version first
        _make_version(db_session, ci.id, normalized_text="old content")
        # Create a newer version
        newer = _make_version(db_session, ci.id, normalized_text="new content")

        results = keyword_search(db_session, "Scraping")
        assert len(results) == 1
        assert results[0]["version_id"] == newer.id

    def test_can_filter_by_source_id(self, db_session):
        """Search can filter results by source_id."""
        from harvester.search.keyword import keyword_search

        src_a = _make_source(db_session, "source_a")
        src_b = _make_source(db_session, "source_b")
        ci_a = _make_item(db_session, "Python Data Analysis", source_id=src_a.id)
        _make_version(db_session, ci_a.id)
        ci_b = _make_item(db_session, "Python Web Development", source_id=src_b.id)
        _make_version(db_session, ci_b.id)

        results = keyword_search(db_session, "Python", source_id=src_a.id)
        assert len(results) == 1
        assert results[0]["item_id"] == ci_a.id

    def test_result_contains_expected_fields(self, db_session):
        """Each result dict should contain the expected keys."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(
            db_session,
            "Test Title",
            source_id=src.id,
        )
        ci.canonical_url = "https://example.com/article"
        session = db_session
        session.flush()
        _make_version(db_session, ci.id)

        results = keyword_search(db_session, "Test")
        assert len(results) == 1
        r = results[0]
        expected_keys = {
            "item_id",
            "title",
            "canonical_url",
            "source_id",
            "version_id",
            "created_at",
        }
        assert set(r.keys()) == expected_keys

    def test_dedup_group_returns_canonical_only(self, db_session):
        """Two versions in same dedup group should return only the canonical one."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci_a = _make_item(db_session, "Dedup Python Article", source_id=src.id)
        ci_b = _make_item(db_session, "Dedup Python Article Copy", source_id=src.id)

        v_a = _make_version(db_session, ci_a.id)
        v_b = _make_version(db_session, ci_b.id)

        # Put both versions in a dedup group with v_a as canonical
        dg = DedupGroup(canonical_item_version_id=v_a.id)
        db_session.add(dg)
        db_session.flush()
        v_a.dedup_group_id = dg.id
        v_b.dedup_group_id = dg.id
        db_session.flush()

        results = keyword_search(db_session, "Python")
        # Only the canonical version should be returned
        version_ids = [r["version_id"] for r in results]
        assert v_a.id in version_ids
        assert v_b.id not in version_ids

    def test_wildcard_percent_treated_as_literal(self, db_session):
        """User input containing % should not act as SQL wildcard."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci_match = _make_item(db_session, "100% Python Guide", source_id=src.id)
        _make_version(db_session, ci_match.id)
        ci_other = _make_item(db_session, "Python Tutorial", source_id=src.id)
        _make_version(db_session, ci_other.id)

        # Searching for literal "100%" should only match the first item
        results = keyword_search(db_session, "100%")
        assert len(results) == 1
        assert results[0]["title"] == "100% Python Guide"

    def test_wildcard_underscore_treated_as_literal(self, db_session):
        """User input containing _ should not act as SQL wildcard."""
        from harvester.search.keyword import keyword_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "test_variable", source_id=src.id)
        _make_version(db_session, ci.id)
        ci_other = _make_item(db_session, "testXvariable", source_id=src.id)
        _make_version(db_session, ci_other.id)

        results = keyword_search(db_session, "test_variable")
        assert len(results) == 1
        assert results[0]["title"] == "test_variable"
