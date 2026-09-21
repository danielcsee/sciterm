"""Database side of the type-ahead's typo search; the scoring is in `prefix.py`.

Three steps, so the expensive work only touches survivors: fetch every name
and mention form sharing the input's first letter (btree prefix indexes),
score them in Python, then resolve the few within tolerance to their entities
with a mention count each.

Mention forms come from `entity_mention_embeddings`, the corpus's list of
distinct surface texts. It is filled by the embedding stage, so a paper's new
wordings become searchable here when its embeddings are written — the same
moment the embedding matcher sees them.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.entity_matching.models import EntityMatch
from api.entity_matching.prefix import (
    PrefixHit,
    first_letter_pattern,
    rank_prefix_hits,
    within_tolerance,
)

NAME_CANDIDATES_SQL = """
SELECT DISTINCT name
FROM entities
WHERE lower(name) LIKE :pattern ESCAPE '\\'
"""

SURFACE_CANDIDATES_SQL = """
SELECT surface_text
FROM entity_mention_embeddings
WHERE lower(surface_text) LIKE :pattern ESCAPE '\\'
"""

#: Entities whose canonical name is one of `:texts`, matched on that name.
ENTITIES_BY_NAME_SQL = """
SELECT e.id AS entity_id, e.identifier, e.entity_type, e.database, e.name,
       e.name AS matched_text
FROM entities e
WHERE e.name = ANY(CAST(:texts AS text[]))
"""

#: Entities written as one of `:texts` somewhere in the corpus.
ENTITIES_BY_SURFACE_SQL = """
SELECT DISTINCT e.id AS entity_id, e.identifier, e.entity_type, e.database,
       e.name, m.surface_text AS matched_text
FROM paper_entity_mentions m
JOIN entities e ON e.id = m.entity_id
WHERE m.surface_text = ANY(CAST(:texts AS text[]))
"""

MENTION_COUNTS_SQL = """
SELECT entity_id, count(*) AS mentions
FROM paper_entity_mentions
WHERE entity_id = ANY(CAST(:entity_ids AS bigint[]))
GROUP BY entity_id
"""


class PrefixMatchManager:
    """Typo-tolerant prefix candidates for one type-ahead input."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(self, query: str, limit: int) -> list[EntityMatch]:
        pattern = first_letter_pattern(query)
        if pattern is None:
            return []
        name_distances = within_tolerance(query, self._texts(NAME_CANDIDATES_SQL, pattern))
        surface_distances = within_tolerance(
            query, self._texts(SURFACE_CANDIDATES_SQL, pattern)
        )
        rows = self._rows(ENTITIES_BY_NAME_SQL, name_distances) + self._rows(
            ENTITIES_BY_SURFACE_SQL, surface_distances
        )
        distances = {**surface_distances, **name_distances}
        hits = self._hits(rows, distances)
        return rank_prefix_hits(query, hits, limit)

    def _texts(self, statement: str, pattern: str) -> list[str]:
        return list(self._session.execute(text(statement), {"pattern": pattern}).scalars())

    def _rows(self, statement: str, distances: dict[str, int]) -> list[object]:
        if not distances:
            return []
        return list(self._session.execute(text(statement), {"texts": list(distances)}))

    def _hits(self, rows: Sequence[object], distances: dict[str, int]) -> list[PrefixHit]:
        """Attach each row's distance and its entity's corpus mention count."""
        mentions = self._mention_counts({row.entity_id for row in rows})
        return [
            PrefixHit(
                entity_id=row.entity_id,
                identifier=row.identifier,
                entity_type=row.entity_type,
                database=row.database,
                name=row.name,
                matched_text=row.matched_text,
                distance=distances[row.matched_text],
                mentions=mentions.get(row.entity_id, 0),
            )
            for row in rows
        ]

    def _mention_counts(self, entity_ids: set[int]) -> dict[int, int]:
        if not entity_ids:
            return {}
        rows = self._session.execute(
            text(MENTION_COUNTS_SQL), {"entity_ids": sorted(entity_ids)}
        )
        return {row.entity_id: row.mentions for row in rows}
