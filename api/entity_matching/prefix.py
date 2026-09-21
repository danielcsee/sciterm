"""Typo-tolerant prefix matching for the type-ahead.

A type-ahead input is the start of a name, so a candidate is scored by how
many edits turn the input into *some prefix* of it, not into the whole name.
Adjacent transpositions count as one edit (optimal string alignment), because
they are the commonest typing slip and the one trigram matching handles
worst: "brac" shares two trigrams with "BRCA1" and scores 0.22, but is one
edit from its prefix "brca".

The tolerance grows with the input, following Elasticsearch's AUTO fuzziness:
none for one or two characters, one edit for three to five, two beyond.

Everything here is pure. `prefix_search.py` fetches the candidates, which are
limited to names sharing the input's first letter.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Optional

from api.entity_matching.models import EntityMatch

#: Input lengths at which one more edit is tolerated.
ONE_EDIT_FROM = 3
TWO_EDITS_FROM = 6


@dataclass(frozen=True)
class PrefixHit:
    """A candidate text within tolerance, resolved to its entity."""

    entity_id: int
    identifier: str
    entity_type: str
    database: str
    name: Optional[str]
    matched_text: str
    distance: int
    #: Occurrences of the entity across the corpus; the tie-breaker.
    mentions: int


def allowed_edits(query: str) -> int:
    """How many edits an input of this length may be away from a match."""
    length = len(query.strip())
    if length >= TWO_EDITS_FROM:
        return 2
    if length >= ONE_EDIT_FROM:
        return 1
    return 0


def first_letter_pattern(query: str) -> Optional[str]:
    """A LIKE pattern for texts starting with the input's first character.

    Lower-cased to match the `lower(...)` indexes, with LIKE's wildcards and
    its escape character escaped. None for blank input.
    """
    stripped = query.strip()
    if not stripped:
        return None
    first = stripped[0].lower()
    if first in {"%", "_", "\\"}:
        first = "\\" + first
    return first + "%"


def prefix_edit_distance(query: str, text: str) -> int:
    """Fewest edits turning `query` into any prefix of `text`, ignoring case.

    Optimal string alignment: insertions, deletions, substitutions, and
    swaps of adjacent characters, each costing one.
    """
    query, text = query.strip().casefold(), text.casefold()
    rows = _alignment_rows(query, text)
    return min(rows[-1])


def within_tolerance(query: str, texts: Iterable[str]) -> dict[str, int]:
    """Each text close enough to be a typo of the input, with its distance."""
    limit = allowed_edits(query)
    close: dict[str, int] = {}
    for text in texts:
        distance = prefix_edit_distance(query, _relevant_prefix(query, text, limit))
        if distance <= limit:
            close[text] = distance
    return close


def rank_prefix_hits(query: str, hits: Sequence[PrefixHit], limit: int) -> list[EntityMatch]:
    """Best hit per entity, fewest edits first, then most mentioned.

    The score is `1 - distance / input length`, so an exact prefix scores 1.
    """
    best = _best_hit_per_entity(hits)
    ordered = sorted(best, key=_hit_order)[:limit]
    length = max(len(query.strip()), 1)
    return [_as_match(hit, 1 - hit.distance / length) for hit in ordered]


def _alignment_rows(query: str, text: str) -> list[list[int]]:
    """The OSA table, one row per query character plus the empty prefix.

    Column j is the distance from the query so far to `text[:j]`, so the last
    row's minimum is the distance to the closest prefix of `text`.
    """
    rows = [list(range(len(text) + 1))]
    for i, query_char in enumerate(query, start=1):
        row = [i]
        for j, text_char in enumerate(text, start=1):
            cost = min(
                rows[i - 1][j] + 1,
                row[j - 1] + 1,
                rows[i - 1][j - 1] + (query_char != text_char),
            )
            if _is_swap(query, text, i, j):
                cost = min(cost, rows[i - 2][j - 2] + 1)
            row.append(cost)
        rows.append(row)
    return rows


def _is_swap(query: str, text: str, i: int, j: int) -> bool:
    return (
        i > 1
        and j > 1
        and query[i - 1] == text[j - 2]
        and query[i - 2] == text[j - 1]
    )


def _relevant_prefix(query: str, text: str, limit: int) -> str:
    """Only the first `len(query) + limit` characters can matter.

    Matching a longer prefix costs at least one deletion per extra character,
    so anything past that point is over the limit already. Trimming keeps a
    long mention form from costing a full table.
    """
    return text[: len(query.strip()) + limit]


def _best_hit_per_entity(hits: Sequence[PrefixHit]) -> list[PrefixHit]:
    best: dict[int, PrefixHit] = {}
    for hit in hits:
        current = best.get(hit.entity_id)
        if current is None or _hit_order(hit) < _hit_order(current):
            best[hit.entity_id] = hit
    return list(best.values())


def _hit_order(hit: PrefixHit) -> tuple[int, int, int, str, int]:
    """Fewest edits, most mentions, shortest text, then alphabetical and id."""
    text = hit.matched_text
    return (hit.distance, -hit.mentions, len(text), text.casefold(), hit.entity_id)


def _as_match(hit: PrefixHit, score: float) -> EntityMatch:
    return EntityMatch(
        entity_id=hit.entity_id,
        identifier=hit.identifier,
        entity_type=hit.entity_type,
        database=hit.database,
        name=hit.name,
        matched_text=hit.matched_text,
        score=round(score, 6),
    )
