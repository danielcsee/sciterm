"""Public response types for the entity-matching experiment."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ExtractionMethod = Literal["noun_phrase", "three_gram"]
MatchMethod = Literal["trigram", "embedding"]
MatchSource = Literal["entity_name", "mention_surface_text"]


class EntityMatch(BaseModel):
    entity_id: int
    identifier: str
    entity_type: str
    database: str
    name: Optional[str] = None
    matched_text: str
    score: float


class EntityMatchGroup(BaseModel):
    """Top candidates from one extraction/matcher/source path."""

    query_fragment: str
    extraction_method: ExtractionMethod
    match_method: MatchMethod
    source: MatchSource
    matches: list[EntityMatch] = Field(default_factory=list)


class FilteredEntityMatch(EntityMatch):
    """A surviving candidate, tagged with the fragment that found it."""

    query_fragment: str


class EntityStrategyGroup(BaseModel):
    """Filtered candidates pooled across every fragment for one strategy."""

    extraction_method: ExtractionMethod
    match_method: MatchMethod
    source: MatchSource
    matches: list[FilteredEntityMatch] = Field(default_factory=list)
