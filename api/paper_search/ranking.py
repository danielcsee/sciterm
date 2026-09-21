"""Pure scoring and slot selection. No database access, so it is unit-tested.

Ranking order: distinct terms matched, then IDF-weighted hits. Selection then
fills `top_k` slots in three passes:

1. Coverage: the paper matching the most terms, ties broken by total hits.
2. Champions: for each term, rarest first, the paper with the most hits of it.
3. Fill: the ranked list, until the slots run out.

A paper that wins several slots takes one and records every reason, which
frees the remaining slots for the fill. The result is returned in rank order.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from api.paper_search.models import PaperScore, SearchTerm, TermHit

COVERAGE_REASON = "broadest coverage"
RANK_REASON = "ranked"


def document_frequencies(hits: Iterable[TermHit], term_count: int) -> list[int]:
    """Papers matching each term, by term index."""
    frequencies = [0] * term_count
    for hit in hits:
        frequencies[hit.term_index] += 1
    return frequencies


def common_terms(
    frequencies: Sequence[int], corpus_size: int, max_fraction: float
) -> set[int]:
    """Terms matching more than `max_fraction` of the corpus.

    If every matched term is that common, the rarest is spared so a query of
    only broad words still returns something.
    """
    if corpus_size <= 0:
        return set()
    common = {
        index
        for index, frequency in enumerate(frequencies)
        if frequency / corpus_size > max_fraction
    }
    matched = {index for index, frequency in enumerate(frequencies) if frequency}
    if matched and matched <= common:
        common.discard(min(matched, key=lambda index: (frequencies[index], index)))
    return common


def term_weights(
    frequencies: Sequence[int], corpus_size: int, dropped: set[int]
) -> list[float]:
    """Smoothed IDF, ln(1 + N / df): positive for any term that matched."""
    return [
        0.0
        if index in dropped or not frequency
        else math.log(1 + corpus_size / frequency)
        for index, frequency in enumerate(frequencies)
    ]


def score_papers(hits: Iterable[TermHit], weights: Sequence[float]) -> list[PaperScore]:
    """One score per paper with at least one hit on a weighted term."""
    papers: dict[int, PaperScore] = {}
    for hit in hits:
        weight = weights[hit.term_index]
        if weight <= 0:
            continue
        paper = papers.setdefault(hit.paper_id, PaperScore(hit.paper_id))
        paper.term_hits[hit.term_index] = hit.hits
        paper.score += weight * math.log(1 + hit.hits)
    return list(papers.values())


def rank(papers: Iterable[PaperScore]) -> list[PaperScore]:
    """Terms matched, then IDF-weighted score, then total hits."""
    return sorted(
        papers,
        key=lambda paper: (-paper.terms_matched, -paper.score, -paper.mentions, paper.paper_id),
    )


def select_papers(
    papers: Sequence[PaperScore],
    terms: Sequence[SearchTerm],
    weights: Sequence[float],
    top_k: int,
) -> list[tuple[PaperScore, list[str]]]:
    """Up to `top_k` papers in rank order, each with why it was chosen."""
    if top_k <= 0 or not papers:
        return []
    ranked = rank(papers)
    reasons: dict[int, list[str]] = {}
    _select_coverage(ranked, reasons)
    _select_champions(ranked, terms, weights, top_k, reasons)
    _fill_by_rank(ranked, top_k, reasons)
    return [(paper, reasons[paper.paper_id]) for paper in ranked if paper.paper_id in reasons]


def champion_reason(term: SearchTerm) -> str:
    return f"most mentions of “{term.phrase}”"


def _select_coverage(ranked: Sequence[PaperScore], reasons: dict[int, list[str]]) -> None:
    # `ranked` is already ordered for stable tie-breaking; max keeps the first.
    coverage = max(ranked, key=lambda paper: (paper.terms_matched, paper.mentions))
    reasons[coverage.paper_id] = [COVERAGE_REASON]


def _select_champions(
    ranked: Sequence[PaperScore],
    terms: Sequence[SearchTerm],
    weights: Sequence[float],
    top_k: int,
    reasons: dict[int, list[str]],
) -> None:
    rarest_first = sorted(
        (index for index, weight in enumerate(weights) if weight > 0),
        key=lambda index: (-weights[index], index),
    )
    for term_index in rarest_first:
        champion = _champion(ranked, term_index)
        if champion is None:
            continue
        if champion.paper_id not in reasons and len(reasons) >= top_k:
            continue
        reasons.setdefault(champion.paper_id, []).append(champion_reason(terms[term_index]))


def _champion(ranked: Sequence[PaperScore], term_index: int) -> PaperScore | None:
    """The paper with the most hits of one term; rank order breaks ties."""
    best: PaperScore | None = None
    for paper in ranked:
        hits = paper.term_hits.get(term_index, 0)
        if hits and (best is None or hits > best.term_hits[term_index]):
            best = paper
    return best


def _fill_by_rank(
    ranked: Sequence[PaperScore], top_k: int, reasons: dict[int, list[str]]
) -> None:
    for paper in ranked:
        if len(reasons) >= top_k:
            return
        reasons.setdefault(paper.paper_id, [RANK_REASON])
