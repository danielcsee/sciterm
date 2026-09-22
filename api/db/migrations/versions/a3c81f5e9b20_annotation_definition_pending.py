"""annotations are saved before their definition arrives

Revision ID: a3c81f5e9b20
Revises: e6b4a2d91c73
Create Date: 2026-09-21 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3c81f5e9b20"
down_revision: Union[str, Sequence[str], None] = "e6b4a2d91c73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_user_annotations_definition", "user_annotations", type_="check")
    op.alter_column("user_annotations", "definition", existing_type=sa.Text(), nullable=True)
    op.create_check_constraint(
        "ck_user_annotations_definition",
        "user_annotations",
        "definition IS NULL OR length(btrim(definition)) > 0",
    )


def downgrade() -> None:
    op.execute("DELETE FROM user_annotations WHERE definition IS NULL")
    op.drop_constraint("ck_user_annotations_definition", "user_annotations", type_="check")
    op.alter_column("user_annotations", "definition", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(
        "ck_user_annotations_definition",
        "user_annotations",
        "length(btrim(definition)) > 0",
    )
