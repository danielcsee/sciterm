"""Type-ahead suggestions: the chat's candidate strategies, merged per entity.

The chat filter (`filtering.py`) does not fit a type-ahead box. It keeps one
candidate per query word, so "tp53" would offer a single entity, and its
cutoffs are calibrated on whole words, so a half-typed "osteop" would clear
none. Suggestions instead take every strategy's candidates as they come from
`EntityMatchManager` — already above its SQL-level thresholds — and merge them.

Trigram and embedding scores are on different scales and cannot be sorted
together, so the merge is by strategy priority: spelling matches before
meaning matches, canonical names before mention text. Within a strategy the
manager's own score order holds. An entity found by several strategies keeps
its first, highest-priority appearance.
"""

from __future__ import annotations

from collections.abc import Sequence

from api.entity_matching.models import EntityMatch, EntityMatchGroup

#: How many suggestions a type-ahead dropdown shows.
SUGGESTION_LIMIT = 10

#: Strategy order for the merge, highest priority first.
STRATEGY_PRIORITY: tuple[tuple[str, str], ...] = (
    ("trigram", "entity_name"),
    ("trigram", "mention_surface_text"),
    ("embedding", "entity_name"),
    ("embedding", "mention_surface_text"),
)


def merge_suggestions(
    groups: Sequence[EntityMatchGroup], limit: int = SUGGESTION_LIMIT
) -> list[EntityMatch]:
    """One candidate per entity, in strategy-priority order, at most `limit`."""
    suggestions: list[EntityMatch] = []
    seen: set[int] = set()
    for match in _in_priority_order(groups):
        if match.entity_id in seen:
            continue
        seen.add(match.entity_id)
        suggestions.append(match)
        if len(suggestions) == limit:
            break
    return suggestions


def _in_priority_order(groups: Sequence[EntityMatchGroup]) -> list[EntityMatch]:
    rank = {strategy: index for index, strategy in enumerate(STRATEGY_PRIORITY)}
    ordered = sorted(
        groups, key=lambda group: rank.get((group.match_method, group.source), len(rank))
    )
    return [match for group in ordered for match in group.matches]
