"""saved AI chats

Revision ID: d7e4a1c92b66
Revises: c3a9e5f17b20
Create Date: 2026-09-21 00:00:00.000000

Durable, owner-scoped chat snapshots with normalized citations and identified
entity pills. Entity candidate/debug output is intentionally absent.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7e4a1c92b66"
down_revision: Union[str, Sequence[str], None] = "c3a9e5f17b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chats",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_free_access_code_id", sa.BigInteger(), nullable=True),
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
            "length(btrim(title)) BETWEEN 1 AND 200", name="ck_ai_chats_title_length"
        ),
        sa.CheckConstraint(
            "NOT (owner_user_id IS NOT NULL AND owner_free_access_code_id IS NOT NULL)",
            name="ck_ai_chats_one_owner",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_free_access_code_id"], ["free_access_codes.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_ai_chats_owner_user_updated", "ai_chats", ["owner_user_id", "updated_at"]
    )
    op.create_index(
        "ix_ai_chats_owner_code_updated",
        "ai_chats",
        ["owner_free_access_code_id", "updated_at"],
    )

    op.create_table(
        "ai_chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("fallback_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_kind", sa.String(length=32), nullable=True),
        sa.Column(
            "result_papers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("papers_considered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "analysis_entity_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "analysis_duplicates_rejected", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("analysis_model", sa.Text(), nullable=True),
        sa.Column("analysis_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_chat_messages_role"),
        sa.CheckConstraint("status IN ('done', 'error')", name="ck_ai_chat_messages_status"),
        sa.CheckConstraint("ordinal >= 0", name="ck_ai_chat_messages_ordinal"),
        sa.ForeignKeyConstraint(["chat_id"], ["ai_chats.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chat_id", "ordinal", name="uq_ai_chat_messages_chat_ordinal"),
        sa.UniqueConstraint("chat_id", "id", name="uq_ai_chat_messages_chat_id"),
    )
    op.create_index("ix_ai_chat_messages_chat", "ai_chat_messages", ["chat_id"])

    op.create_table(
        "ai_chat_citations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("assistant_message_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.BigInteger(), nullable=True),
        sa.Column("chunk_id", sa.BigInteger(), nullable=True),
        sa.Column("paper_chunk_ordinal", sa.Integer(), nullable=False),
        sa.Column("paper_pmid_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("paper_title_snapshot", sa.Text(), nullable=True),
        sa.Column("section_type", sa.String(length=32), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("selected_by", sa.Text(), nullable=False),
        sa.CheckConstraint("number > 0", name="ck_ai_chat_citations_number"),
        sa.CheckConstraint("position >= 0", name="ck_ai_chat_citations_position"),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"], ["ai_chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["paper_chunks.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "assistant_message_id", "number", name="uq_ai_chat_citations_message_number"
        ),
        sa.UniqueConstraint(
            "assistant_message_id", "position", name="uq_ai_chat_citations_message_position"
        ),
    )
    op.create_index(
        "ix_ai_chat_citations_message", "ai_chat_citations", ["assistant_message_id"]
    )

    op.create_table(
        "ai_chat_message_entities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("assistant_message_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("identifier_snapshot", sa.Text(), nullable=False),
        sa.Column("entity_type_snapshot", sa.String(length=32), nullable=False),
        sa.Column("name_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "phrases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.CheckConstraint("position >= 0", name="ck_ai_chat_message_entities_position"),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"], ["ai_chat_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "assistant_message_id",
            "position",
            name="uq_ai_chat_message_entities_message_position",
        ),
    )
    op.create_index(
        "ix_ai_chat_message_entities_message",
        "ai_chat_message_entities",
        ["assistant_message_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_chat_message_entities_message", table_name="ai_chat_message_entities"
    )
    op.drop_table("ai_chat_message_entities")
    op.drop_index("ix_ai_chat_citations_message", table_name="ai_chat_citations")
    op.drop_table("ai_chat_citations")
    op.drop_index("ix_ai_chat_messages_chat", table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")
    op.drop_index("ix_ai_chats_owner_code_updated", table_name="ai_chats")
    op.drop_index("ix_ai_chats_owner_user_updated", table_name="ai_chats")
    op.drop_table("ai_chats")
