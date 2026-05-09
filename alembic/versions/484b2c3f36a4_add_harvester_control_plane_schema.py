"""add harvester control plane schema

Revision ID: 484b2c3f36a4
Revises:
Create Date: 2026-05-09 18:17:10.431580
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "484b2c3f36a4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Independent tables (no FK dependencies) ---

    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column(
            "before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_action", "audit_events", ["action"], unique=False
    )
    op.create_index(
        "ix_audit_events_created_at", "audit_events", ["created_at"], unique=False
    )
    op.create_index(
        "ix_audit_events_entity",
        "audit_events",
        ["entity_type", "entity_id"],
        unique=False,
    )

    op.create_table(
        "dedup_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("canonical_item_version_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dedup_groups")),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_jobs_idempotency_key")),
    )
    op.create_index("ix_jobs_locked_until", "jobs", ["locked_until"], unique=False)
    op.create_index("ix_jobs_run_after", "jobs", ["run_after"], unique=False)
    op.create_index(
        "ix_jobs_status_priority", "jobs", ["status", "priority"], unique=False
    )

    op.create_table(
        "recipes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("executor", sa.String(length=64), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "auth_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipes")),
    )

    op.create_table(
        "topic_watches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_watches")),
    )

    # --- sources depends on recipes ---

    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trust_level", sa.String(length=16), nullable=False),
        sa.Column("auth_required", sa.Boolean(), nullable=False),
        sa.Column("default_recipe_id", sa.UUID(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["default_recipe_id"],
            ["recipes.id"],
            name=op.f("fk_sources_default_recipe_id_recipes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_sources_name")),
    )

    # --- content_items depends on sources, topic_watches ---

    op.create_table(
        "content_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("external_item_id", sa.String(length=512), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("topic_watch_id", sa.UUID(), nullable=True),
        sa.Column("original_url", sa.Text(), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("canonical_url_hash", sa.String(length=64), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_content_items_source_id_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_watch_id"],
            ["topic_watches.id"],
            name=op.f("fk_content_items_topic_watch_id_topic_watches"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_items")),
        sa.UniqueConstraint(
            "source_id", "external_item_id", name="uq_content_items_source_external_id"
        ),
    )
    op.create_index(
        "ix_content_items_canonical_url_hash",
        "content_items",
        ["canonical_url_hash"],
        unique=False,
    )
    op.create_index(
        "ix_content_items_status", "content_items", ["status"], unique=False
    )

    # --- raw_objects depends on sources ---

    op.create_table(
        "raw_objects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("retention_policy", sa.String(length=32), nullable=True),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("compressed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_raw_objects_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_objects")),
    )

    # --- item_versions depends on content_items, raw_objects, dedup_groups ---

    op.create_table(
        "item_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("simhash", sa.String(length=64), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("raw_object_id", sa.UUID(), nullable=True),
        sa.Column("dedup_group_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_item_versions_content_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dedup_group_id"],
            ["dedup_groups.id"],
            name=op.f("fk_item_versions_dedup_group_id_dedup_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_object_id"],
            ["raw_objects.id"],
            name=op.f("fk_item_versions_raw_object_id_raw_objects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_versions")),
        sa.UniqueConstraint(
            "content_item_id", "content_hash", name="uq_item_versions_content_hash"
        ),
    )

    # --- chunks depends on item_versions ---

    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_version_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding_status", sa.String(length=32), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_version_id"],
            ["item_versions.id"],
            name=op.f("fk_chunks_item_version_id_item_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
    )
    op.create_index(
        "ix_chunks_item_version_id", "chunks", ["item_version_id"], unique=False
    )

    # --- source_frontiers depends on sources ---

    op.create_table(
        "source_frontiers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=True),
        sa.Column(
            "frontier_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("rewind_window", sa.Integer(), nullable=True),
        sa.Column(
            "last_complete_range",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_source_frontiers_source_id_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_frontiers")),
        sa.UniqueConstraint(
            "source_id", name=op.f("uq_source_frontiers_source_id")
        ),
    )

    # --- topic_sources depends on topic_watches, sources ---

    op.create_table(
        "topic_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("topic_watch_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_topic_sources_source_id_sources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_watch_id"],
            ["topic_watches.id"],
            name=op.f("fk_topic_sources_topic_watch_id_topic_watches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_sources")),
        sa.UniqueConstraint(
            "topic_watch_id", "source_id", name="uq_topic_sources_pair"
        ),
    )

    # --- crawl_runs depends on sources, topic_watches, recipes, raw_objects ---

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("topic_watch_id", sa.UUID(), nullable=True),
        sa.Column("recipe_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fetch_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("raw_object_id", sa.UUID(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["raw_object_id"],
            ["raw_objects.id"],
            name=op.f("fk_crawl_runs_raw_object_id_raw_objects"),
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_crawl_runs_recipe_id_recipes"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_crawl_runs_source_id_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_watch_id"],
            ["topic_watches.id"],
            name=op.f("fk_crawl_runs_topic_watch_id_topic_watches"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crawl_runs")),
    )

    # --- item_observations depends on content_items, raw_objects ---

    op.create_table(
        "item_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("raw_object_id", sa.UUID(), nullable=False),
        sa.Column("extraction_run_id", sa.UUID(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("observed_url", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_item_observations_content_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_object_id"],
            ["raw_objects.id"],
            name=op.f("fk_item_observations_raw_object_id_raw_objects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_observations")),
    )

    # --- Deferred FK: dedup_groups -> item_versions (circular dependency) ---
    op.create_foreign_key(
        op.f("fk_dedup_groups_canonical_item_version_id_item_versions"),
        "dedup_groups",
        "item_versions",
        ["canonical_item_version_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop deferred FK first
    op.drop_constraint(
        op.f("fk_dedup_groups_canonical_item_version_id_item_versions"),
        "dedup_groups",
        type_="foreignkey",
    )
    op.drop_table("item_observations")
    op.drop_table("crawl_runs")
    op.drop_table("topic_sources")
    op.drop_table("source_frontiers")
    op.drop_index("ix_chunks_item_version_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("item_versions")
    op.drop_index("ix_content_items_status", table_name="content_items")
    op.drop_index(
        "ix_content_items_canonical_url_hash", table_name="content_items"
    )
    op.drop_table("content_items")
    op.drop_table("raw_objects")
    op.drop_table("sources")
    op.drop_table("topic_watches")
    op.drop_table("recipes")
    op.drop_index("ix_jobs_status_priority", table_name="jobs")
    op.drop_index("ix_jobs_run_after", table_name="jobs")
    op.drop_index("ix_jobs_locked_until", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("dedup_groups")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")
    op.execute("DROP EXTENSION IF EXISTS vector")
