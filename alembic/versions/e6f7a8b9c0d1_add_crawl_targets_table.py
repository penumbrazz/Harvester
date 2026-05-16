"""add crawl_targets table

Revision ID: e6f7a8b9c0d1
Revises: d5a1b2c3e4f6
Create Date: 2026-05-16 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5a1b2c3e4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawl_targets",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipe_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id"),
            nullable=False,
        ),
        sa.Column(
            "parent_target_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("crawl_targets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "discovered_from_raw_object_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_objects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("canonical_url_hash", sa.String(64), nullable=False),
        sa.Column("target_role", sa.String(32), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("external_item_id", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_raw_object_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_objects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
    )
    op.create_index(
        "ix_crawl_targets_source_status",
        "crawl_targets",
        ["source_id", "status"],
    )
    op.create_index(
        "ix_crawl_targets_parent_target_id",
        "crawl_targets",
        ["parent_target_id"],
    )
    op.create_index(
        "ix_crawl_targets_last_seen_at",
        "crawl_targets",
        ["last_seen_at"],
    )
    op.create_index(
        "ix_crawl_targets_external_item_id",
        "crawl_targets",
        ["external_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_targets_external_item_id", table_name="crawl_targets")
    op.drop_index("ix_crawl_targets_last_seen_at", table_name="crawl_targets")
    op.drop_index("ix_crawl_targets_parent_target_id", table_name="crawl_targets")
    op.drop_index("ix_crawl_targets_source_status", table_name="crawl_targets")
    op.drop_table("crawl_targets")
