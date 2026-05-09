"""add job source_id and lane for queue fairness

Revision ID: c4d8e2f9b3a5
Revises: b3c7f1d8a2e4
Create Date: 2026-05-09 20:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4d8e2f9b3a5'
down_revision: Union[str, None] = 'b3c7f1d8a2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column('source_id', sa.String(36), nullable=True),
    )
    op.add_column(
        'jobs',
        sa.Column('lane', sa.String(64), nullable=True),
    )
    op.create_index(
        'ix_jobs_source_id', 'jobs', ['source_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_jobs_source_id', table_name='jobs')
    op.drop_column('jobs', 'lane')
    op.drop_column('jobs', 'source_id')
