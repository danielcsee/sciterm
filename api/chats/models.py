"""SQLAlchemy metadata for saved AI chats and their durable presentation data."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class AiChat(Base):
    __tablename__ = "ai_chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    owner_free_access_code_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("free_access_codes.id", ondelete="CASCADE")
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(btrim(title)) BETWEEN 1 AND 200", name="ck_ai_chats_title_length"
        ),
        CheckConstraint(
            "NOT (owner_user_id IS NOT NULL AND owner_free_access_code_id IS NOT NULL)",
            name="ck_ai_chats_one_owner",
        ),
        Index("ix_ai_chats_owner_user_updated", "owner_user_id", "updated_at"),
        Index(
            "ix_ai_chats_owner_code_updated", "owner_free_access_code_id", "updated_at"
        ),
    )


class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_chats.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_text: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    response_kind: Mapped[Optional[str]] = mapped_column(String(32))
    result_papers: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    papers_considered: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    analysis_entity_ids: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    analysis_duplicates_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    analysis_model: Mapped[Optional[str]] = mapped_column(Text)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_chat_messages_role"),
        CheckConstraint(
            "status IN ('pending', 'done', 'error')", name="ck_ai_chat_messages_status"
        ),
        CheckConstraint("ordinal >= 0", name="ck_ai_chat_messages_ordinal"),
        UniqueConstraint("chat_id", "ordinal", name="uq_ai_chat_messages_chat_ordinal"),
        UniqueConstraint("chat_id", "id", name="uq_ai_chat_messages_chat_id"),
        Index("ix_ai_chat_messages_chat", "chat_id"),
    )


class AiChatCitation(Base):
    __tablename__ = "ai_chat_citations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assistant_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_chat_messages.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    paper_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("papers.id", ondelete="SET NULL")
    )
    chunk_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("paper_chunks.id", ondelete="SET NULL")
    )
    paper_chunk_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    paper_pmid_snapshot: Mapped[Optional[int]] = mapped_column(BigInteger)
    paper_title_snapshot: Mapped[Optional[str]] = mapped_column(Text)
    section_type: Mapped[Optional[str]] = mapped_column(String(32))
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)
    selected_by: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("number > 0", name="ck_ai_chat_citations_number"),
        CheckConstraint("position >= 0", name="ck_ai_chat_citations_position"),
        UniqueConstraint(
            "assistant_message_id", "number", name="uq_ai_chat_citations_message_number"
        ),
        UniqueConstraint(
            "assistant_message_id", "position", name="uq_ai_chat_citations_message_position"
        ),
        Index("ix_ai_chat_citations_message", "assistant_message_id"),
    )


class AiChatMessageEntity(Base):
    __tablename__ = "ai_chat_message_entities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assistant_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_chat_messages.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("entities.id", ondelete="SET NULL")
    )
    identifier_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    name_snapshot: Mapped[Optional[str]] = mapped_column(Text)
    phrases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_ai_chat_message_entities_position"),
        UniqueConstraint(
            "assistant_message_id",
            "position",
            name="uq_ai_chat_message_entities_message_position",
        ),
        Index("ix_ai_chat_message_entities_message", "assistant_message_id"),
    )
