"""Database access for paper search: one manager over one session."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.db.models import PaperStageRun
from api.paper_search.models import EvidenceChunk, SearchTerm, TermHit
from api.paper_search.queries import (
    CORPUS_SIZE_SQL,
    ENTITY_CHUNKS_SQL,
    ENTITY_HITS_SQL,
    PAPER_METADATA_SQL,
    TEXT_CHUNKS_SQL,
    TEXT_HITS_SQL,
)

#: Display fields for a paper, keyed by column name.
PaperMetadata = dict[str, object]


class PaperSearchManager:
    """Run paper-search queries. Read-only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def corpus_size(self) -> int:
        return self._session.scalar(
            text(CORPUS_SIZE_SQL), {"final_stage": PaperStageRun.FINAL_STAGE}
        ) or 0

    def entity_hits(self, terms: Sequence[SearchTerm]) -> list[TermHit]:
        """Mentions of each term's entities, per paper."""
        pairs = [
            (index, entity_id)
            for index, term in enumerate(terms)
            for entity_id in term.entity_ids
        ]
        if not pairs:
            return []
        rows = self._session.execute(
            text(ENTITY_HITS_SQL),
            {
                "term_indexes": [index for index, _ in pairs],
                "entity_ids": [entity_id for _, entity_id in pairs],
                "final_stage": PaperStageRun.FINAL_STAGE,
            },
        )
        return [TermHit(row.paper_id, row.term_index, row.hits) for row in rows]

    def text_hits(self, terms: Sequence[SearchTerm]) -> list[TermHit]:
        """Chunks matching each term's phrase, per paper."""
        if not terms:
            return []
        rows = self._session.execute(
            text(TEXT_HITS_SQL),
            {
                "phrases": [term.phrase for term in terms],
                "final_stage": PaperStageRun.FINAL_STAGE,
            },
        )
        return [TermHit(row.paper_id, row.term_index, row.hits) for row in rows]

    def entity_chunks(
        self, paper_ids: Sequence[int], terms: Sequence[SearchTerm], per_paper: int
    ) -> dict[int, list[EvidenceChunk]]:
        """Each paper's chunks with the most mentions of the terms' entities."""
        entity_ids = [entity_id for term in terms for entity_id in term.entity_ids]
        if not paper_ids or not entity_ids or per_paper <= 0:
            return {}
        return self._chunks(
            ENTITY_CHUNKS_SQL,
            {"paper_ids": list(paper_ids), "entity_ids": entity_ids, "per_paper": per_paper},
        )

    def text_chunks(
        self, paper_ids: Sequence[int], terms: Sequence[SearchTerm], per_paper: int
    ) -> dict[int, list[EvidenceChunk]]:
        """Each paper's chunks ranked by full-text relevance to the phrases."""
        if not paper_ids or not terms or per_paper <= 0:
            return {}
        return self._chunks(
            TEXT_CHUNKS_SQL,
            {
                "paper_ids": list(paper_ids),
                "phrases": [term.phrase for term in terms],
                "per_paper": per_paper,
            },
        )

    def papers(self, paper_ids: Sequence[int]) -> dict[int, PaperMetadata]:
        if not paper_ids:
            return {}
        rows = self._session.execute(text(PAPER_METADATA_SQL), {"paper_ids": list(paper_ids)})
        return {row.id: dict(row._mapping) for row in rows}

    def _chunks(
        self, statement: str, params: dict[str, object]
    ) -> dict[int, list[EvidenceChunk]]:
        chunks: dict[int, list[EvidenceChunk]] = {}
        for row in self._session.execute(text(statement), params):
            chunks.setdefault(row.paper_id, []).append(
                EvidenceChunk(
                    chunk_id=row.chunk_id,
                    section_type=row.section_type,
                    text=row.text,
                    score=round(float(row.score), 6),
                )
            )
        return chunks
