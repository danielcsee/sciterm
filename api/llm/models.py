"""Public response types for intent routing."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from api.llm.tools import IntentToolName


class IntentEntity(BaseModel):
    """A candidate entity the model confirmed, with the phrase that named it."""

    entity_id: int
    identifier: str
    entity_type: str
    name: Optional[str] = None
    phrase: str


class IntentResult(BaseModel):
    """Which tool the model routed the query to, and the entities it resolved."""

    tool: IntentToolName
    entities: list[IntentEntity] = Field(default_factory=list)
    #: Only `no_match` explains itself.
    reason: Optional[str] = None
    model: str
