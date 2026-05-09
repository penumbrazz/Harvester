"""Tests for vector (embedding) search over chunks.

These tests exercise the ``vector_search`` function which performs
nearest-neighbor queries against the chunk embeddings using cosine
distance.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from harvester.db.models import Chunk, ContentItem, DedupGroup, ItemVersion, Source


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


def _make_version(session: Session, content_item_id: uuid.UUID) -> ItemVersion:
    """Create and persist an ItemVersion."""
    iv = ItemVersion(
        content_item_id=content_item_id,
        content_hash=uuid.uuid4().hex,
    )
    session.add(iv)
    session.flush()
    return iv


def _make_chunk(
    session: Session,
    item_version_id: uuid.UUID,
    chunk_index: int,
    text: str,
    embedding: list[float] | None = None,
    embedding_status: str = "pending",
) -> Chunk:
    """Create and persist a Chunk row."""
    chunk = Chunk(
        item_version_id=item_version_id,
        chunk_index=chunk_index,
        text=text,
        embedding_status=embedding_status,
        embedding=embedding,
    )
    session.add(chunk)
    session.flush()
    return chunk


def _dummy_embedding(seed: int = 0) -> list[float]:
    """Produce a deterministic unit-normalized 1536-d embedding."""
    dim = 1536
    vals = [0.0] * dim
    # Simple pattern: set a few positions to create a direction
    vals[seed % dim] = 1.0
    vals[(seed + 1) % dim] = 0.5
    vals[(seed + 2) % dim] = 0.3
    # Normalize
    norm = sum(v * v for v in vals) ** 0.5
    return [v / norm for v in vals]


class TestVectorSearch:
    """Tests for the vector_search function."""

    def test_vector_search_returns_nearest_neighbors(self, db_session):
        """Vector search over chunks.embedding returns nearest neighbors."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Embedding Test", src.id)
        iv = _make_version(db_session, ci.id)
        emb = _dummy_embedding(seed=42)
        _make_chunk(
            db_session, iv.id, 0, "test chunk text", embedding=emb, embedding_status="ready"
        )

        results = vector_search(db_session, emb, limit=5)
        assert len(results) >= 1
        assert results[0]["chunk_id"] is not None

    def test_empty_embedding_returns_no_results(self, db_session):
        """A zero-vector embedding returns no results."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Empty Emb", src.id)
        iv = _make_version(db_session, ci.id)
        _make_chunk(db_session, iv.id, 0, "no embedding", embedding_status="pending")

        # A zero vector should not crash but returns nothing useful
        zero = [0.0] * 1536
        results = vector_search(db_session, zero, limit=5)
        # The chunk has no embedding (NULL), so it shouldn't match
        assert len(results) == 0

    def test_can_limit_number_of_results(self, db_session):
        """The limit parameter controls the maximum number of results."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Limit Test", src.id)
        iv = _make_version(db_session, ci.id)
        # Create 5 chunks with slightly different embeddings
        for i in range(5):
            emb = _dummy_embedding(seed=i)
            _make_chunk(
                db_session, iv.id, i, f"chunk {i}", embedding=emb, embedding_status="ready"
            )

        results = vector_search(db_session, _dummy_embedding(seed=0), limit=2)
        assert len(results) == 2

    def test_results_include_item_version_and_content_item_info(self, db_session):
        """Results include item version and content item context."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Context Test", src.id)
        iv = _make_version(db_session, ci.id)
        emb = _dummy_embedding(seed=10)
        _make_chunk(db_session, iv.id, 0, "context chunk", embedding=emb, embedding_status="ready")

        results = vector_search(db_session, emb, limit=5)
        assert len(results) == 1
        r = results[0]
        assert r["item_version_id"] == iv.id
        assert r["content_item_id"] == ci.id
        assert r["title"] == "Context Test"
        assert r["text"] == "context chunk"

    def test_distance_is_cosine(self, db_session):
        """The distance metric used should be cosine (<=>)."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Distance Test", src.id)
        iv = _make_version(db_session, ci.id)
        emb = _dummy_embedding(seed=99)
        _make_chunk(db_session, iv.id, 0, "distance chunk", embedding=emb, embedding_status="ready")

        # The same vector should have cosine distance ~0
        results = vector_search(db_session, emb, limit=1)
        assert len(results) == 1
        # Cosine distance of a vector with itself is 0
        assert results[0]["distance"] < 0.01

    def test_ignores_chunks_without_ready_embedding(self, db_session):
        """Chunks with embedding_status != 'ready' are excluded."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci = _make_item(db_session, "Pending Test", src.id)
        iv = _make_version(db_session, ci.id)
        emb = _dummy_embedding(seed=7)
        # Chunk has embedding but status is 'pending'
        _make_chunk(db_session, iv.id, 0, "pending chunk", embedding=emb, embedding_status="pending")

        results = vector_search(db_session, emb, limit=5)
        assert len(results) == 0

    def test_dedup_group_returns_canonical_only(self, db_session):
        """Chunks from versions in the same dedup group return only canonical."""
        from harvester.search.vector import vector_search

        src = _make_source(db_session)
        ci_a = _make_item(db_session, "Dedup Article A", src.id)
        ci_b = _make_item(db_session, "Dedup Article B", src.id)

        v_a = _make_version(db_session, ci_a.id)
        v_b = _make_version(db_session, ci_b.id)

        emb_a = _dummy_embedding(seed=50)
        emb_b = _dummy_embedding(seed=51)
        _make_chunk(db_session, v_a.id, 0, "canonical chunk", embedding=emb_a, embedding_status="ready")
        _make_chunk(db_session, v_b.id, 0, "duplicate chunk", embedding=emb_b, embedding_status="ready")

        # Put both versions in a dedup group with v_a as canonical
        dg = DedupGroup(canonical_item_version_id=v_a.id)
        db_session.add(dg)
        db_session.flush()
        v_a.dedup_group_id = dg.id
        v_b.dedup_group_id = dg.id
        db_session.flush()

        results = vector_search(db_session, emb_a, limit=10)
        version_ids = {r["item_version_id"] for r in results}
        assert v_a.id in version_ids
        assert v_b.id not in version_ids
