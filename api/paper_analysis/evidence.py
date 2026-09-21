"""Choose, de-duplicate and number the paragraphs an analysis is grounded in."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.orm import Session

from api.paper_analysis.dedupe import drop_near_duplicates
from api.paper_analysis.manager import ParagraphManager, ParagraphRow
from api.paper_analysis.models import (
    Citation,
    Evidence,
    ParagraphHit,
    PickedParagraph,
)
from api.paper_analysis.selection import select_paragraphs
from api.paper_search import SearchedPaper, SearchMethod, SearchTermSummary

log = logging.getLogger(__name__)


def gather_evidence(
    session: Session,
    method: SearchMethod,
    terms: Sequence[SearchTermSummary],
    papers: Sequence[SearchedPaper],
    *,
    dense_per_paper: int,
    duplicate_similarity: float,
) -> Evidence:
    """The selected papers' best paragraphs, minus near-copies, numbered.

    `terms` must be the search's own summaries: their positions are the term
    indexes, and their weights are the IDF the papers were ranked by.
    """
    manager = ParagraphManager(session)
    paper_ids = [paper.paper_id for paper in papers]
    hits = _paragraph_hits(manager, method, paper_ids, terms)
    picks = select_paragraphs(hits, [term.weight for term in terms], dense_per_paper)
    ordered = priority_order(paper_ids, picks)
    kept, rejected = drop_near_duplicates(
        [pick.chunk_id for pick in ordered],
        manager.similarities([pick.chunk_id for pick in ordered]),
        duplicate_similarity,
    )
    if rejected:
        log.info("paper analysis rejected near-duplicate chunks %s", rejected)
    kept_ids = set(kept)
    kept_picks = [pick for pick in ordered if pick.chunk_id in kept_ids]
    return Evidence(
        citations=number_citations(paper_ids, kept_picks, manager.paragraphs(kept)),
        rejected=len(rejected),
    )


def query_entity_ids(terms: Sequence[SearchTermSummary]) -> list[int]:
    """Every entity id behind a scored term, once each, in term order."""
    ids: list[int] = []
    for term in terms:
        if term.weight <= 0:
            continue
        ids.extend(entity_id for entity_id in term.entity_ids if entity_id not in ids)
    return ids


def priority_order(
    paper_ids: Sequence[int], picks: Mapping[int, Sequence[PickedParagraph]]
) -> list[PickedParagraph]:
    """Paper rank order, then pick order: who wins when two are duplicates."""
    return [pick for paper_id in paper_ids for pick in picks.get(paper_id, [])]


def number_citations(
    paper_ids: Sequence[int],
    picks: Sequence[PickedParagraph],
    rows: Mapping[int, ParagraphRow],
) -> list[Citation]:
    """Number from 1, grouped by paper in rank order, reading order within one.

    Grouping keeps one paper's citations adjacent, which is how the UI shows
    them; reading order makes `[1]` precede `[2]` in the paper itself.
    """
    rank = {paper_id: index for index, paper_id in enumerate(paper_ids)}
    present = [pick for pick in picks if pick.chunk_id in rows]
    present.sort(key=lambda pick: (rank[pick.paper_id], rows[pick.chunk_id]["ordinal"]))
    return [
        _citation(number, pick, rows[pick.chunk_id])
        for number, pick in enumerate(present, start=1)
    ]


def _paragraph_hits(
    manager: ParagraphManager,
    method: SearchMethod,
    paper_ids: Sequence[int],
    terms: Sequence[SearchTermSummary],
) -> list[ParagraphHit]:
    if method == "entity":
        return manager.entity_hits(paper_ids, terms)
    return manager.text_hits(paper_ids, terms)


def _citation(number: int, pick: PickedParagraph, row: ParagraphRow) -> Citation:
    return Citation(
        number=number,
        paper_id=pick.paper_id,
        chunk_id=pick.chunk_id,
        ordinal=row["ordinal"],
        section_type=row["section_type"],
        text=row["text"],
        selected_by=pick.reason,
    )
