"""Shared fixtures and helpers for worker tests."""

import uuid

from sqlalchemy.orm import Session

from harvester.db.models import Chunk, ContentItem, ItemVersion, Source


def make_source(session: Session, name: str = "test_source") -> Source:
    """Create and persist a Source row."""
    src = Source(name=name, kind="rss")
    session.add(src)
    session.flush()
    return src


def make_item(session: Session, title: str, source_id: uuid.UUID) -> ContentItem:
    """Create and persist a ContentItem."""
    ci = ContentItem(item_type="article", title=title, source_id=source_id)
    session.add(ci)
    session.flush()
    return ci


def make_version(session: Session, content_item_id: uuid.UUID) -> ItemVersion:
    """Create and persist an ItemVersion."""
    iv = ItemVersion(
        content_item_id=content_item_id,
        content_hash=uuid.uuid4().hex,
    )
    session.add(iv)
    session.flush()
    return iv


def make_chunk(
    session: Session,
    item_version_id: uuid.UUID,
    chunk_index: int,
    text: str,
    embedding_status: str = "pending",
) -> Chunk:
    """Create and persist a Chunk row."""
    chunk = Chunk(
        item_version_id=item_version_id,
        chunk_index=chunk_index,
        text=text,
        embedding_status=embedding_status,
    )
    session.add(chunk)
    session.flush()
    return chunk


def make_full_chain(session: Session, title: str = "test"):
    """Create source → item → version and return (source, item, version)."""
    src = make_source(session, name=f"{title}_src")
    ci = make_item(session, title, src.id)
    iv = make_version(session, ci.id)
    return src, ci, iv
