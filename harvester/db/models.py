"""SQLAlchemy models for the Harvester control plane schema."""

import datetime
import uuid

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from harvester.adapters.embedding_settings import EmbeddingSettings
from harvester.db.base import Base

EMBEDDING_DIMENSION = EmbeddingSettings().dimension


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


# ---------------------------------------------------------------------------
# Sources and Topics
# ---------------------------------------------------------------------------


class Source(Base):
    """A fixed or configurable information source."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    trust_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )
    auth_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failure_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class TopicWatch(Base):
    """A temporary topic watch that tracks specific subjects across sources."""

    __tablename__ = "topic_watches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class TopicSource(Base):
    """Association between topic watches and sources."""

    __tablename__ = "topic_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_watch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topic_watches.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "topic_watch_id", "source_id", name="uq_topic_sources_pair"
        ),
    )


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------


class Recipe(Base):
    """A crawl/extraction recipe defining how to process a source."""

    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    executor: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    approval_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auth_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


# ---------------------------------------------------------------------------
# Crawl Runs and Raw Objects
# ---------------------------------------------------------------------------


class CrawlRun(Base):
    """A single crawl execution event."""

    __tablename__ = "crawl_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    topic_watch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topic_watches.id"), nullable=True
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    fetch_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_objects.id"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class RawObject(Base):
    """Raw fetch evidence with metadata but no inline payload."""

    __tablename__ = "raw_objects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_policy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retain_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    compressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


# ---------------------------------------------------------------------------
# Crawl Targets
# ---------------------------------------------------------------------------


class CrawlTarget(Base):
    """A discovered URL target controlled by a fixed source boundary."""

    __tablename__ = "crawl_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False
    )
    parent_target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_targets.id", ondelete="SET NULL"),
        nullable=True,
    )
    discovered_from_raw_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_objects.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    target_role: Mapped[str] = mapped_column(String(32), nullable=False)
    media_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown"
    )
    external_item_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_raw_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_objects.id", ondelete="SET NULL"),
        nullable=True,
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        sa.CheckConstraint(
            "target_role IN ('list', 'detail', 'asset')",
            name="ck_crawl_targets_target_role",
        ),
        sa.CheckConstraint(
            "media_type IN ('html', 'pdf', 'unknown')",
            name="ck_crawl_targets_media_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'skipped')",
            name="ck_crawl_targets_status",
        ),
        sa.CheckConstraint("depth >= 0", name="ck_crawl_targets_depth"),
        sa.CheckConstraint("failure_count >= 0", name="ck_crawl_targets_failure_count"),
        sa.UniqueConstraint(
            "source_id",
            "target_role",
            "canonical_url_hash",
            name="uq_crawl_targets_source_role_canonical",
        ),
        sa.Index("ix_crawl_targets_source_status", "source_id", "status"),
        sa.Index("ix_crawl_targets_parent_target_id", "parent_target_id"),
        sa.Index("ix_crawl_targets_last_seen_at", "last_seen_at"),
        sa.Index("ix_crawl_targets_external_item_id", "external_item_id"),
    )


# ---------------------------------------------------------------------------
# Content Items and Observations
# ---------------------------------------------------------------------------


class ContentItem(Base):
    """An extracted content item from one or more raw objects."""

    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_item_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    topic_watch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topic_watches.id"), nullable=True
    )
    original_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "source_id",
            "external_item_id",
            name="uq_content_items_source_external_id",
        ),
        sa.Index("ix_content_items_canonical_url_hash", "canonical_url_hash"),
        sa.Index("ix_content_items_status", "status"),
    )


class ItemObservation(Base):
    """An observation of a content item from a specific raw object."""

    __tablename__ = "item_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_objects.id"), nullable=False
    )
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_seen: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=_utcnow
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "content_item_id",
            "raw_object_id",
            name="uq_item_observations_item_raw",
        ),
    )


# ---------------------------------------------------------------------------
# Item Versions and Dedup
# ---------------------------------------------------------------------------


class DedupGroup(Base):
    """A group of equivalent item versions."""

    __tablename__ = "dedup_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_item_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_versions.id"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class ItemVersion(Base):
    """A version of a content item with content hash for dedup."""

    __tablename__ = "item_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    simhash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_objects.id"), nullable=True
    )
    dedup_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dedup_groups.id"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "content_item_id",
            "content_hash",
            name="uq_item_versions_content_hash",
        ),
    )


# ---------------------------------------------------------------------------
# Chunks (with pgvector embedding column)
# ---------------------------------------------------------------------------


class Chunk(Base):
    """A text chunk from an item version, with optional embedding."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    embedding: Mapped[list | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (sa.Index("ix_chunks_item_version_id", "item_version_id"),)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class Job(Base):
    """A queued job with lease, retry and idempotency support."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_after: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lane: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        sa.Index("ix_jobs_status_priority", "status", "priority"),
        sa.Index("ix_jobs_run_after", "run_after"),
        sa.Index("ix_jobs_locked_until", "locked_until"),
        sa.Index("ix_jobs_source_id", "source_id"),
    )


# ---------------------------------------------------------------------------
# Source Frontiers
# ---------------------------------------------------------------------------


class SourceFrontier(Base):
    """Cursor and frontier state for high-frequency sources."""

    __tablename__ = "source_frontiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cursor_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    frontier_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rewind_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_complete_range: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


# ---------------------------------------------------------------------------
# Watch Schedules
# ---------------------------------------------------------------------------


class WatchSchedule(Base):
    """A recurring crawl schedule for a source or topic-source pair."""

    __tablename__ = "watch_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_watch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topic_watches.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    next_run_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_enqueued_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lane: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        sa.Index(
            "ix_watch_schedules_status_next_run_at",
            "status",
            "next_run_at",
        ),
    )


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


class AuditEvent(Base):
    """An audit event recording state changes and important pipeline decisions."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        sa.Index("ix_audit_events_entity", "entity_type", "entity_id"),
        sa.Index("ix_audit_events_action", "action"),
        sa.Index("ix_audit_events_created_at", "created_at"),
    )
