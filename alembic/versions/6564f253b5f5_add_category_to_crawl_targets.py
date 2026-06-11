"""add_category_to_crawl_targets

Revision ID: 6564f253b5f5
Revises: f7a8b9c0d1e2
Create Date: 2026-05-20 21:43:06.988898
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6564f253b5f5"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crawl_targets", sa.Column("category", sa.String(length=128), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("crawl_targets", "category")
