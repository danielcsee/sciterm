"""Entity group tables: a named, ordered set of corpus entities.

Groups are global, like the corpus itself: anyone can read and edit any group,
so there is no owner column. Names are unique ignoring case, enforced by an
expression index rather than application code, so two concurrent saves cannot
both win.

The schema lives in the Alembic chain; these classes exist so the metadata
matches it and autogenerate does not propose dropping the tables.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base

#: The unique index on lower(name). Routes match on this name to tell a
#: duplicate from any other integrity error.
UNIQUE_NAME_INDEX = "uq_entity_groups_lower_name"


class EntityGroup(Base):
    __tablename__ = "entity_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    #: Stored trimmed; the check keeps a blank name out even if a caller
    #: bypasses the API's validation.
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 100", name="ck_entity_groups_name_length"
        ),
        Index(UNIQUE_NAME_INDEX, text("lower(name)"), unique=True),
    )


class EntityGroupMember(Base):
    """One entity in one group. `position` is the order the chips were added."""

    __tablename__ = "entity_group_members"

    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (Index("ix_entity_group_members_entity_id", "entity_id"),)
