"""chunk full text search

Revision ID: a7d3e6f19b42
Revises: 3b0d52a8c144
Create Date: 2026-09-21 00:00:00.000000

Paper search falls back to full-text search over chunk text when a chat query
names no entities. The tsvector is a stored generated column, so existing rows
are filled by this migration and new rows by Postgres on insert.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = "a7d3e6f19b42"
down_revision: Union[str, Sequence[str], None] = "3b0d52a8c144"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "paper_chunks",
        sa.Column(
            "text_search",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_paper_chunks_text_search",
        "paper_chunks",
        ["text_search"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_paper_chunks_text_search", table_name="paper_chunks")
    op.drop_column("paper_chunks", "text_search")
