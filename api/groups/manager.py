"""Database access for entity groups: one manager over one session."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.groups.models import UNIQUE_NAME_INDEX
from api.groups.queries import (
    DELETE_GROUP_SQL,
    DELETE_MEMBERS_SQL,
    GROUPS_SQL,
    INSERT_GROUP_SQL,
    INSERT_MEMBERS_SQL,
    MISSING_ENTITIES_SQL,
    UPDATE_GROUP_SQL,
)
from api.groups.schemas import EntityGroupOut, GroupEntity


class DuplicateGroupNameError(Exception):
    """Another group already has this name, ignoring case."""


class GroupManager:
    """Read and write `entity_groups` and their members."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_groups(self) -> list[EntityGroupOut]:
        return _assemble_groups(self._session.execute(text(GROUPS_SQL), {"group_id": None}))

    def get_group(self, group_id: int) -> Optional[EntityGroupOut]:
        groups = _assemble_groups(
            self._session.execute(text(GROUPS_SQL), {"group_id": group_id})
        )
        return groups[0] if groups else None

    def missing_entities(self, entity_ids: Sequence[int]) -> list[int]:
        rows = self._session.execute(
            text(MISSING_ENTITIES_SQL), {"entity_ids": list(entity_ids)}
        )
        return [row.entity_id for row in rows]

    def create(self, name: str, entity_ids: Sequence[int]) -> int:
        """Insert a group and its members; raises `DuplicateGroupNameError`."""
        group_id = self._write_name(INSERT_GROUP_SQL, {"name": name})
        self._insert_members(group_id, entity_ids)
        return group_id

    def update(
        self,
        group_id: int,
        name: Optional[str],
        entity_ids: Optional[Sequence[int]],
    ) -> bool:
        """Rename and/or replace members. False if the group does not exist."""
        updated = self._write_name(UPDATE_GROUP_SQL, {"name": name, "group_id": group_id})
        if updated is None:
            return False
        if entity_ids is not None:
            self._session.execute(text(DELETE_MEMBERS_SQL), {"group_id": group_id})
            self._insert_members(group_id, entity_ids)
        return True

    def delete(self, group_id: int) -> bool:
        row = self._session.execute(text(DELETE_GROUP_SQL), {"group_id": group_id}).first()
        return row is not None

    def _write_name(self, statement: str, params: dict[str, object]) -> Optional[int]:
        """Run an insert/update of the name, translating the unique-name clash."""
        try:
            return self._session.execute(text(statement), params).scalar_one_or_none()
        except IntegrityError as exc:
            if UNIQUE_NAME_INDEX in str(exc.orig):
                raise DuplicateGroupNameError(str(params["name"])) from exc
            raise

    def _insert_members(self, group_id: int, entity_ids: Sequence[int]) -> None:
        self._session.execute(
            text(INSERT_MEMBERS_SQL),
            {"group_id": group_id, "entity_ids": list(entity_ids)},
        )


def _assemble_groups(rows: object) -> list[EntityGroupOut]:
    """Fold one-row-per-member results into groups, keeping row order."""
    groups: dict[int, EntityGroupOut] = {}
    for row in rows:
        group = groups.get(row.group_id)
        if group is None:
            group = groups[row.group_id] = EntityGroupOut(
                group_id=row.group_id,
                name=row.group_name,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        if row.entity_id is not None:
            group.entities.append(_group_entity(row))
    return list(groups.values())


def _group_entity(row: object) -> GroupEntity:
    return GroupEntity(
        entity_id=row.entity_id,
        identifier=row.identifier,
        entity_type=row.entity_type,
        database=row.database,
        name=row.entity_name,
        names=[row.surface_text] if row.surface_text else [],
    )
