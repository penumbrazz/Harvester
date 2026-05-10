"""add watch_schedules table

Revision ID: d5a1b2c3e4f6
Revises: c4d8e2f9b3a5
Create Date: 2026-05-10 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd5a1b2c3e4f6'
down_revision: Union[str, None] = 'c4d8e2f9b3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'watch_schedules',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'schedule_key',
            sa.String(255),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            'source_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('sources.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'topic_watch_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('topic_watches.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'recipe_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('recipes.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.String(32),
            nullable=False,
            server_default='active',
        ),
        sa.Column(
            'interval_seconds',
            sa.Integer,
            nullable=False,
        ),
        sa.Column(
            'next_run_at',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            'last_enqueued_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            'priority',
            sa.Integer,
            nullable=False,
            server_default='0',
        ),
        sa.Column(
            'lane',
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_watch_schedules_status_next_run_at',
        'watch_schedules',
        ['status', 'next_run_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_watch_schedules_status_next_run_at',
        table_name='watch_schedules',
    )
    op.drop_table('watch_schedules')
