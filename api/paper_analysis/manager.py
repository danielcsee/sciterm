"""Database access for paper analysis: one manager over one session."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.paper_analysis.dedupe import Similarities
from api.paper_analysis.models import ParagraphHit
from api.paper_analysis.queries import (
    PARAGRAPH_ENTITY_HITS_SQL,
    PARAGRAPH_SIMILARITIES_SQL,
    PARAGRAPH_TEXT_HITS_SQL,
    PARAGRAPHS_SQL,
    PROSE_CHUNK_TYPES,
    PROSE_SECTIONS,
)
from api.paper_search import SearchTermSummary

#: A candidate paragraph's display fields, keyed by column name.
ParagraphRow = dict[str, object]


class ParagraphManager:
    """Run paper-analysis queries. Read-only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def entity_hits(
        self, paper_ids: Sequence[int], terms: Sequence[SearchTermSummary]
    ) -> list[ParagraphHit]:
        """Mentions of each term's entities, per prose paragraph."""
        pairs = [
            (index, entity_id)
            for index, term in enumerate(terms)
            for entity_id in term.entity_ids
        ]
        if not paper_ids or not pairs:
            return []
        return self._hits(
            PARAGRAPH_ENTITY_HITS_SQL,
            {
                "paper_ids": list(paper_ids),
                "term_indexes": [index for index, _ in pairs],
                "entity_ids": [entity_id for _, entity_id in pairs],
            },
        )

    def text_hits(
        self, paper_ids: Sequence[int], terms: Sequence[SearchTermSummary]
    ) -> list[ParagraphHit]:
        """Full-text rank of each term's phrase, per prose paragraph."""
        if not paper_ids or not terms:
            return []
        return self._hits(
            PARAGRAPH_TEXT_HITS_SQL,
            {"paper_ids": list(paper_ids), "phrases": [term.phrase for term in terms]},
        )

    def similarities(self, chunk_ids: Sequence[int]) -> Similarities:
        if len(chunk_ids) < 2:
            return {}
        rows = self._session.execute(
            text(PARAGRAPH_SIMILARITIES_SQL), {"chunk_ids": list(chunk_ids)}
        )
        return {frozenset((row.a_id, row.b_id)): float(row.similarity) for row in rows}

    def paragraphs(self, chunk_ids: Sequence[int]) -> dict[int, ParagraphRow]:
        if not chunk_ids:
            return {}
        rows = self._session.execute(text(PARAGRAPHS_SQL), {"chunk_ids": list(chunk_ids)})
        return {row.chunk_id: dict(row._mapping) for row in rows}

    def _hits(
        self, statement: str, params: dict[str, object]
    ) -> list[ParagraphHit]:
        rows = self._session.execute(
            text(statement),
            {**params, "chunk_types": PROSE_CHUNK_TYPES, "section_types": PROSE_SECTIONS},
        )
        return [
            ParagraphHit(row.paper_id, row.chunk_id, row.term_index, float(row.hits))
            for row in rows
        ]
