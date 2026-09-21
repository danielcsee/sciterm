"""The paper search behind the `paper_search` and `paper_analysis` tools."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy.orm import Session

from api.entity_matching import QueryFragment
from api.llm.models import IntentEntity
from api.paper_search.manager import PaperMetadata, PaperSearchManager
from api.paper_search.models import (
    EvidenceChunk,
    PaperScore,
    PaperSearchResult,
    SearchedPaper,
    SearchMethod,
    SearchTerm,
    SearchTermSummary,
    TermHit,
)
from api.paper_search.ranking import (
    common_terms,
    document_frequencies,
    score_papers,
    select_papers,
    term_weights,
)
from api.paper_search.terms import entity_terms, noun_phrase_terms

log = logging.getLogger(__name__)


def search_papers(
    session: Session,
    entities: Sequence[IntentEntity],
    fragments: Sequence[QueryFragment],
    *,
    top_k: int,
    chunks_per_paper: int,
    max_term_fraction: float,
) -> PaperSearchResult:
    """Search by confirmed entities, or by noun phrases when there are none.

    Only the full-text path drops overly common terms: confirmed entities were
    already judged relevant by the model, while a noun phrase can be as broad
    as "the role".
    """
    manager = PaperSearchManager(session)
    if entities:
        terms = entity_terms(entities)
        method: SearchMethod = "entity"
        hits = manager.entity_hits(terms)
        max_fraction = None
    else:
        terms = noun_phrase_terms(fragments)
        method = "full_text"
        hits = manager.text_hits(terms)
        max_fraction = max_term_fraction
    return _rank_and_select(
        manager, method, terms, hits, top_k, chunks_per_paper, max_fraction
    )


def _rank_and_select(
    manager: PaperSearchManager,
    method: SearchMethod,
    terms: Sequence[SearchTerm],
    hits: Sequence[TermHit],
    top_k: int,
    chunks_per_paper: int,
    max_fraction: float | None,
) -> PaperSearchResult:
    corpus_size = manager.corpus_size()
    frequencies = document_frequencies(hits, len(terms))
    dropped = (
        common_terms(frequencies, corpus_size, max_fraction)
        if max_fraction is not None
        else set()
    )
    weights = term_weights(frequencies, corpus_size, dropped)
    scores = score_papers(hits, weights)
    selected = select_papers(scores, terms, weights, top_k)
    summaries = _term_summaries(terms, frequencies, weights, dropped)
    if dropped:
        log.info("paper search dropped common terms %s", [terms[i].phrase for i in sorted(dropped)])

    scored_terms = [term for index, term in enumerate(terms) if weights[index] > 0]
    papers = _build_papers(manager, method, selected, scored_terms, chunks_per_paper)
    return PaperSearchResult(
        method=method, terms=summaries, papers_considered=len(scores), papers=papers
    )


def _term_summaries(
    terms: Sequence[SearchTerm],
    frequencies: Sequence[int],
    weights: Sequence[float],
    dropped: set[int],
) -> list[SearchTermSummary]:
    return [
        SearchTermSummary(
            phrase=term.phrase,
            entity_ids=list(term.entity_ids),
            papers_matched=frequencies[index],
            weight=round(weights[index], 6),
            dropped=index in dropped,
        )
        for index, term in enumerate(terms)
    ]


def _build_papers(
    manager: PaperSearchManager,
    method: SearchMethod,
    selected: Sequence[tuple[PaperScore, list[str]]],
    scored_terms: Sequence[SearchTerm],
    chunks_per_paper: int,
) -> list[SearchedPaper]:
    """Attach metadata and evidence passages to the selected papers."""
    paper_ids = [score.paper_id for score, _ in selected]
    metadata = manager.papers(paper_ids)
    if method == "entity":
        chunks = manager.entity_chunks(paper_ids, scored_terms, chunks_per_paper)
    else:
        chunks = manager.text_chunks(paper_ids, scored_terms, chunks_per_paper)
    return [
        _searched_paper(metadata[score.paper_id], score, reasons, chunks.get(score.paper_id, []))
        for score, reasons in selected
    ]


def _searched_paper(
    metadata: PaperMetadata,
    score: PaperScore,
    reasons: list[str],
    chunks: list[EvidenceChunk],
) -> SearchedPaper:
    return SearchedPaper(
        paper_id=score.paper_id,
        pmid=metadata["pmid"],
        pmcid=metadata["pmcid"],
        title=metadata["title"],
        journal=metadata["journal"],
        pub_year=metadata["pub_year"],
        terms_matched=score.terms_matched,
        mentions=score.mentions,
        score=round(score.score, 6),
        selected_by=reasons,
        chunks=chunks,
    )
