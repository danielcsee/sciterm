"""incremental chats and user annotations

Revision ID: e6b4a2d91c73
Revises: d7e4a1c92b66
Create Date: 2026-09-21 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6b4a2d91c73"
down_revision: Union[str, Sequence[str], None] = "d7e4a1c92b66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_ai_chat_messages_status", "ai_chat_messages", type_="check")
    op.create_check_constraint(
        "ck_ai_chat_messages_status",
        "ai_chat_messages",
        "status IN ('pending', 'done', 'error')",
    )
    op.create_table(
        "user_annotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_free_access_code_id", sa.BigInteger(), nullable=True),
        sa.Column("ai_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("ai_chat_message_id", sa.Uuid(), nullable=True),
        sa.Column("paper_id", sa.BigInteger(), nullable=True),
        sa.Column("paper_chunk_id", sa.BigInteger(), nullable=True),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("phrase", sa.Text(), nullable=False),
        sa.Column("surrounding_context", sa.Text(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("quote_exact", sa.Text(), nullable=False),
        sa.Column("quote_prefix", sa.Text(), nullable=True),
        sa.Column("quote_suffix", sa.Text(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "(ai_chat_id IS NOT NULL) <> (paper_id IS NOT NULL)",
            name="ck_user_annotations_one_source",
        ),
        sa.CheckConstraint(
            "(ai_chat_id IS NULL) = (ai_chat_message_id IS NULL)",
            name="ck_user_annotations_chat_message_required",
        ),
        sa.CheckConstraint(
            "paper_id IS NOT NULL OR paper_chunk_id IS NULL",
            name="ck_user_annotations_paper_chunk_source",
        ),
        sa.CheckConstraint(
            "NOT (owner_user_id IS NOT NULL AND owner_free_access_code_id IS NOT NULL)",
            name="ck_user_annotations_one_owner",
        ),
        sa.CheckConstraint(
            "(start_offset IS NULL AND end_offset IS NULL) OR "
            "(start_offset >= 0 AND end_offset > start_offset)",
            name="ck_user_annotations_offsets",
        ),
        sa.CheckConstraint("position >= 0", name="ck_user_annotations_position"),
        sa.CheckConstraint(
            "length(btrim(source_key)) > 0", name="ck_user_annotations_source_key"
        ),
        sa.CheckConstraint("length(btrim(phrase)) > 0", name="ck_user_annotations_phrase"),
        sa.CheckConstraint(
            "length(btrim(quote_exact)) > 0", name="ck_user_annotations_quote"
        ),
        sa.CheckConstraint(
            "length(btrim(definition)) > 0", name="ck_user_annotations_definition"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_free_access_code_id"], ["free_access_codes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ai_chat_id"], ["ai_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ai_chat_id", "ai_chat_message_id"],
            ["ai_chat_messages.chat_id", "ai_chat_messages.id"],
            ondelete="CASCADE",
            name="fk_user_annotations_chat_message",
        ),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["paper_chunk_id"], ["paper_chunks.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_user_annotations_chat_position", "user_annotations", ["ai_chat_id", "position"]
    )
    op.create_index(
        "ix_user_annotations_paper_position", "user_annotations", ["paper_id", "position"]
    )
    op.create_index(
        "ix_user_annotations_owner_user_updated",
        "user_annotations",
        ["owner_user_id", "updated_at"],
    )
    op.create_index(
        "ix_user_annotations_owner_code_updated",
        "user_annotations",
        ["owner_free_access_code_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_annotations_owner_code_updated", table_name="user_annotations")
    op.drop_index("ix_user_annotations_owner_user_updated", table_name="user_annotations")
    op.drop_index("ix_user_annotations_paper_position", table_name="user_annotations")
    op.drop_index("ix_user_annotations_chat_position", table_name="user_annotations")
    op.drop_table("user_annotations")
    op.drop_constraint("ck_ai_chat_messages_status", "ai_chat_messages", type_="check")
    op.create_check_constraint(
        "ck_ai_chat_messages_status",
        "ai_chat_messages",
        "status IN ('done', 'error')",
    )
