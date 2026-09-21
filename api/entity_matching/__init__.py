"""Candidate entity matching for chat queries."""

from api.entity_matching.extraction import QueryFragment, extract_query_fragments
from api.entity_matching.filtering import filter_entity_matches
from api.entity_matching.models import (
    EntityMatch,
    EntityMatchGroup,
    EntityStrategyGroup,
    FilteredEntityMatch,
)
from api.entity_matching.search import EntityMatchManager

__all__ = [
    "EntityMatch",
    "EntityMatchGroup",
    "EntityMatchManager",
    "EntityStrategyGroup",
    "FilteredEntityMatch",
    "QueryFragment",
    "extract_query_fragments",
    "filter_entity_matches",
]
