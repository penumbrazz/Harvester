"""change chunk embedding column dimension to match configured dimension

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-17 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_DIMENSION = 1536


def _target_dimension() -> int:
    from harvester.adapters.embedding_settings import EmbeddingSettings

    return EmbeddingSettings().dimension


def upgrade() -> None:
    target = _target_dimension()
    if target == OLD_DIMENSION:
        return
    # Clear existing embeddings — dimension change invalidates them.
    # Chunks will be re-embedded by the worker once it picks them up.
    op.execute("UPDATE chunks SET embedding = NULL, embedding_status = 'pending'")
    op.execute(
        f"ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({target})"
    )


def downgrade() -> None:
    op.execute("UPDATE chunks SET embedding = NULL, embedding_status = 'pending'")
    op.execute(
        f"ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({OLD_DIMENSION})"
    )
