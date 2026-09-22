"""SQLAlchemy metadata for user-requested definitions."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class UserAnnotation(Base):
    """One durable definition and the text selector that produced it."""

    __tablename__ = "user_annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    owner_free_access_code_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("free_access_codes.id", ondelete="CASCADE")
    )
    ai_chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("ai_chats.id", ondelete="CASCADE")
    )
    ai_chat_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    paper_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("papers.id", ondelete="CASCADE")
    )
    paper_chunk_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("paper_chunks.id", ondelete="SET NULL")
    )
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    surrounding_context: Mapped[Optional[str]] = mapped_column(Text)
    #: Null while the definition is being generated, or if generating it failed.
    definition: Mapped[Optional[str]] = mapped_column(Text)
    quote_exact: Mapped[str] = mapped_column(Text, nullable=False)
    quote_prefix: Mapped[Optional[str]] = mapped_column(Text)
    quote_suffix: Mapped[Optional[str]] = mapped_column(Text)
    start_offset: Mapped[Optional[int]] = mapped_column(Integer)
    end_offset: Mapped[Optional[int]] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["ai_chat_id", "ai_chat_message_id"],
            ["ai_chat_messages.chat_id", "ai_chat_messages.id"],
            ondelete="CASCADE",
            name="fk_user_annotations_chat_message",
        ),
        CheckConstraint(
            "(ai_chat_id IS NOT NULL) <> (paper_id IS NOT NULL)",
            name="ck_user_annotations_one_source",
        ),
        CheckConstraint(
            "(ai_chat_id IS NULL) = (ai_chat_message_id IS NULL)",
            name="ck_user_annotations_chat_message_required",
        ),
        CheckConstraint(
            "paper_id IS NOT NULL OR paper_chunk_id IS NULL",
            name="ck_user_annotations_paper_chunk_source",
        ),
        CheckConstraint(
            "NOT (owner_user_id IS NOT NULL AND owner_free_access_code_id IS NOT NULL)",
            name="ck_user_annotations_one_owner",
        ),
        CheckConstraint(
            "(start_offset IS NULL AND end_offset IS NULL) OR "
            "(start_offset >= 0 AND end_offset > start_offset)",
            name="ck_user_annotations_offsets",
        ),
        CheckConstraint("position >= 0", name="ck_user_annotations_position"),
        CheckConstraint("length(btrim(source_key)) > 0", name="ck_user_annotations_source_key"),
        CheckConstraint("length(btrim(phrase)) > 0", name="ck_user_annotations_phrase"),
        CheckConstraint("length(btrim(quote_exact)) > 0", name="ck_user_annotations_quote"),
        CheckConstraint(
            "definition IS NULL OR length(btrim(definition)) > 0",
            name="ck_user_annotations_definition",
        ),
        Index("ix_user_annotations_chat_position", "ai_chat_id", "position"),
        Index("ix_user_annotations_paper_position", "paper_id", "position"),
        Index("ix_user_annotations_owner_user_updated", "owner_user_id", "updated_at"),
        Index(
            "ix_user_annotations_owner_code_updated",
            "owner_free_access_code_id",
            "updated_at",
        ),
    )
