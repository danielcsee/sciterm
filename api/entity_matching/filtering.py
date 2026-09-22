"""Reduce raw candidate groups to the few worth acting on per strategy."""

from __future__ import annotations

from collections.abc import Sequence

from api.entity_matching.cutoffs import MatchCutoffs
from api.entity_matching.models import (
    EntityMatchGroup,
    EntityStrategyGroup,
    ExtractionMethod,
    FilteredEntityMatch,
    MatchMethod,
    MatchSource,
)

MAX_CANDIDATES_PER_STRATEGY = 5

StrategyKey = tuple[ExtractionMethod, MatchMethod, MatchSource]


def filter_entity_matches(
    groups: Sequence[EntityMatchGroup],
    query: str,
    cutoffs: MatchCutoffs,
    *,
    max_per_strategy: int = MAX_CANDIDATES_PER_STRATEGY,
) -> list[EntityStrategyGroup]:
    """Dedupe, keep the top candidates per strategy, then drop low scores.

    A strategy is one extraction/matcher/source path pooled across fragments.
    Short texts keep fewer candidates: one per word, up to `max_per_strategy`.
    Each matcher is held to its own cutoff, since their scores are not
    comparable.
    """
    limit = candidate_limit(query, max_per_strategy)
    filtered: list[EntityStrategyGroup] = []
    for (extraction, method, source), candidates in _pool_by_strategy(groups).items():
        top = _dedupe_by_text(candidates)[:limit]
        cutoff = cutoffs.for_method(method)
        filtered.append(
            EntityStrategyGroup(
                extraction_method=extraction,
                match_method=method,
                source=source,
                matches=[match for match in top if match.score >= cutoff],
            )
        )
    return filtered


def candidate_limit(query: str, max_per_strategy: int = MAX_CANDIDATES_PER_STRATEGY) -> int:
    """`max_per_strategy` candidates, or one per word when the text is shorter."""
    return min(max_per_strategy, len(query.split()))


def _pool_by_strategy(
    groups: Sequence[EntityMatchGroup],
) -> dict[StrategyKey, list[FilteredEntityMatch]]:
    pooled: dict[StrategyKey, list[FilteredEntityMatch]] = {}
    for group in groups:
        key = (group.extraction_method, group.match_method, group.source)
        pooled.setdefault(key, []).extend(
            FilteredEntityMatch(**match.model_dump(), query_fragment=group.query_fragment)
            for match in group.matches
        )
    return pooled


def _dedupe_by_text(
    candidates: Sequence[FilteredEntityMatch],
) -> list[FilteredEntityMatch]:
    """Keep the best-scoring candidate per lowercased matched text, best first."""
    best: dict[str, FilteredEntityMatch] = {}
    for candidate in candidates:
        key = candidate.matched_text.lower()
        if key not in best or candidate.score > best[key].score:
            best[key] = candidate
    return sorted(best.values(), key=lambda match: match.score, reverse=True)
