"""entity prefix indexes

Revision ID: c3a9e5f17b20
Revises: b8f3c2d61e47
Create Date: 2026-09-21 00:00:00.000000

The type-ahead's typo search fetches every name and mention form sharing the
typed text's first letter: `lower(x) LIKE 'b%'`. text_pattern_ops lets LIKE use
a btree whatever the database collation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3a9e5f17b20"
down_revision: Union[str, Sequence[str], None] = "b8f3c2d61e47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_entities_lower_name_prefix",
        "entities",
        [sa.text("lower(name) text_pattern_ops")],
    )
    op.create_index(
        "ix_entity_mention_embeddings_lower_surface_prefix",
        "entity_mention_embeddings",
        [sa.text("lower(surface_text) text_pattern_ops")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entity_mention_embeddings_lower_surface_prefix",
        table_name="entity_mention_embeddings",
    )
    op.drop_index("ix_entities_lower_name_prefix", table_name="entities")
