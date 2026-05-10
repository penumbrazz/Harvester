"""Shared test factory functions for inserting test data via raw SQL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session


def _now() -> datetime:
    return datetime.now(UTC)


def insert_source(session: Session, name: str) -> uuid.UUID:
    """Insert a source row and return its id."""
    src_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO sources "
            "(id, name, kind, status, trust_level, auth_required, failure_count, created_at, updated_at) "
            "VALUES (:id, :name, 'rss', 'watched', 'medium', false, 0, :ts, :ts)"
        ),
        {"id": src_id, "name": name, "ts": _now()},
    )
    return src_id


def insert_topic(session: Session, name: str) -> uuid.UUID:
    """Insert a topic_watch row and return its id."""
    tw_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO topic_watches (id, name, query, status, created_at, updated_at) "
            "VALUES (:id, :name, :query, 'active', :ts, :ts)"
        ),
        {"id": tw_id, "name": name, "query": "test", "ts": _now()},
    )
    return tw_id


def insert_content_item(
    session: Session,
    source_id: uuid.UUID,
    title: str,
    *,
    topic_watch_id: uuid.UUID | None = None,
    canonical_url: str | None = None,
) -> uuid.UUID:
    """Insert a content_item row and return its id."""
    ci_id = uuid.uuid4()
    url = canonical_url or f"https://example.com/{uuid.uuid4().hex[:8]}"
    session.execute(
        sa.text(
            "INSERT INTO content_items "
            "(id, item_type, title, source_id, topic_watch_id, "
            "canonical_url, canonical_url_hash, status, created_at, updated_at) "
            "VALUES (:id, 'article', :title, :source_id, :tw_id, "
            ":url, md5(:url), 'active', :ts, :ts)"
        ),
        {
            "id": ci_id,
            "title": title,
            "source_id": source_id,
            "tw_id": topic_watch_id,
            "url": url,
            "ts": _now(),
        },
    )
    return ci_id


def insert_item_version(session: Session, content_item_id: uuid.UUID) -> uuid.UUID:
    """Insert an item_version row and return its id."""
    iv_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO item_versions "
            "(id, content_item_id, content_hash, created_at) "
            "VALUES (:id, :ci_id, :hash, :ts)"
        ),
        {"id": iv_id, "ci_id": content_item_id, "hash": uuid.uuid4().hex, "ts": _now()},
    )
    return iv_id


def insert_chunk(
    session: Session,
    item_version_id: uuid.UUID,
    chunk_index: int,
    text: str,
    *,
    embedding: list[float] | None = None,
    embedding_status: str = "pending",
) -> uuid.UUID:
    """Insert a chunk row and return its id."""
    chunk_id = uuid.uuid4()
    if embedding is not None:
        assert all(isinstance(v, (int, float)) for v in embedding), (
            "embedding values must be numeric"
        )
        emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
        session.execute(
            sa.text(
                "INSERT INTO chunks "
                "(id, item_version_id, chunk_index, text, embedding_status, embedding, created_at) "
                f"VALUES (:id, :iv_id, :idx, :text, :status, '{emb_str}'::vector, :ts)"
            ),
            {
                "id": chunk_id,
                "iv_id": item_version_id,
                "idx": chunk_index,
                "text": text,
                "status": embedding_status,
                "ts": _now(),
            },
        )
    else:
        session.execute(
            sa.text(
                "INSERT INTO chunks "
                "(id, item_version_id, chunk_index, text, embedding_status, created_at) "
                "VALUES (:id, :iv_id, :idx, :text, :status, :ts)"
            ),
            {
                "id": chunk_id,
                "iv_id": item_version_id,
                "idx": chunk_index,
                "text": text,
                "status": embedding_status,
                "ts": _now(),
            },
        )
    return chunk_id


def dummy_embedding(seed: int = 0) -> list[float]:
    """Produce a deterministic unit-normalized 1536-d embedding."""
    dim = 1536
    vals = [0.0] * dim
    vals[seed % dim] = 1.0
    vals[(seed + 1) % dim] = 0.5
    vals[(seed + 2) % dim] = 0.3
    norm = sum(v * v for v in vals) ** 0.5
    return [v / norm for v in vals]
