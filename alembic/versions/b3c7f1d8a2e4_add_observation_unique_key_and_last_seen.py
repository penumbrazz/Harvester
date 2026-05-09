"""add observation unique key and last_seen

Revision ID: b3c7f1d8a2e4
Revises: a96be82a295e
Create Date: 2026-05-09 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b3c7f1d8a2e4'
down_revision: Union[str, None] = 'a96be82a295e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'item_observations',
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        'uq_item_observations_item_raw',
        'item_observations',
        ['content_item_id', 'raw_object_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_item_observations_item_raw', 'item_observations', type_='unique')
    op.drop_column('item_observations', 'last_seen')
