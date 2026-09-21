"""Request and response shapes for the group and entity-suggestion routes."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field, field_validator

MAX_NAME_LENGTH = 100
MAX_GROUP_ENTITIES = 100

#: Type-ahead input bounds. Below two characters trigram matching is noise.
MIN_SUGGEST_LENGTH = 2
MAX_SUGGEST_LENGTH = 100


class GroupEntity(BaseModel):
    """An entity in a group, shaped for the UI's `entityLabel`."""

    entity_id: int
    identifier: str
    entity_type: str
    database: str
    name: Optional[str] = None
    #: The corpus's commonest wording, only when `name` is missing or is the
    #: identifier. Empty otherwise.
    names: list[str] = Field(default_factory=list)


class EntityGroupOut(BaseModel):
    group_id: int
    name: str
    created_at: dt.datetime
    updated_at: dt.datetime
    entities: list[GroupEntity] = Field(default_factory=list)


class EntityGroupList(BaseModel):
    groups: list[EntityGroupOut] = Field(default_factory=list)


class CreateGroupRequest(BaseModel):
    name: str = Field(..., max_length=MAX_NAME_LENGTH)
    entity_ids: list[int] = Field(..., min_length=1, max_length=MAX_GROUP_ENTITIES)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("entity_ids")
    @classmethod
    def _entity_ids(cls, value: list[int]) -> list[int]:
        return dedupe_ids(value)


class UpdateGroupRequest(BaseModel):
    """Either field may be left out; `entity_ids` replaces the whole list."""

    name: Optional[str] = Field(None, max_length=MAX_NAME_LENGTH)
    entity_ids: Optional[list[int]] = Field(
        None, min_length=1, max_length=MAX_GROUP_ENTITIES
    )

    @field_validator("name")
    @classmethod
    def _name(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else clean_name(value)

    @field_validator("entity_ids")
    @classmethod
    def _entity_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return None if value is None else dedupe_ids(value)


class SuggestedEntity(BaseModel):
    """One type-ahead candidate, with the text that matched it."""

    entity_id: int
    identifier: str
    entity_type: str
    database: str
    name: Optional[str] = None
    matched_text: str


class EntitySuggestions(BaseModel):
    query: str
    entities: list[SuggestedEntity] = Field(default_factory=list)


def clean_name(value: str) -> str:
    """Trim a group name; a blank one is rejected rather than stored."""
    name = value.strip()
    if not name:
        raise ValueError("a group needs a name")
    return name


def dedupe_ids(values: list[int]) -> list[int]:
    """Drop repeated ids, keeping first-seen order: that order is chip order."""
    ids = list(dict.fromkeys(values))
    if any(entity_id < 1 for entity_id in ids):
        raise ValueError("entity ids are positive")
    return ids
