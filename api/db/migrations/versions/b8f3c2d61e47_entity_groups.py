"""entity groups

Revision ID: b8f3c2d61e47
Revises: a7d3e6f19b42
Create Date: 2026-09-21 00:00:00.000000

Named, ordered sets of corpus entities. Names are unique ignoring case, so the
index is on lower(name) rather than a plain unique column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8f3c2d61e47"
down_revision: Union[str, Sequence[str], None] = "a7d3e6f19b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entity_groups",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 100", name="ck_entity_groups_name_length"
        ),
    )
    op.create_index(
        "uq_entity_groups_lower_name",
        "entity_groups",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "entity_group_members",
        sa.Column(
            "group_id",
            sa.BigInteger(),
            sa.ForeignKey("entity_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "entity_id",
            sa.BigInteger(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_entity_group_members_entity_id", "entity_group_members", ["entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_entity_group_members_entity_id", table_name="entity_group_members")
    op.drop_table("entity_group_members")
    op.drop_index("uq_entity_groups_lower_name", table_name="entity_groups")
    op.drop_table("entity_groups")
