"""Pure paragraph selection. No database access, so it is unit-tested.

Per paper:

1. Density: the `dense_count` paragraphs with the most hits, summed over every
   query term.
2. Breadth: the paragraph matching the most distinct terms, ties broken by
   Σ IDF × ln(1 + hits), the same scoring `api.paper_search.ranking` uses for
   papers. It is only added when it matches more terms than every density
   pick; otherwise it is just the next-densest paragraph and adds nothing.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from api.paper_analysis.models import ParagraphHit, ParagraphScore, PickedParagraph

DENSITY_REASON = "most mentions"
BREADTH_REASON = "broadest coverage"


def score_paragraphs(
    hits: Iterable[ParagraphHit], weights: Sequence[float]
) -> dict[int, list[ParagraphScore]]:
    """Paragraphs per paper, counting only terms with a positive weight."""
    paragraphs: dict[int, ParagraphScore] = {}
    for hit in hits:
        if weights[hit.term_index] <= 0 or hit.hits <= 0:
            continue
        paragraph = paragraphs.setdefault(
            hit.chunk_id, ParagraphScore(hit.paper_id, hit.chunk_id)
        )
        paragraph.term_hits[hit.term_index] = (
            paragraph.term_hits.get(hit.term_index, 0) + hit.hits
        )
    by_paper: dict[int, list[ParagraphScore]] = {}
    for paragraph in paragraphs.values():
        by_paper.setdefault(paragraph.paper_id, []).append(paragraph)
    return by_paper


def select_paragraphs(
    hits: Iterable[ParagraphHit], weights: Sequence[float], dense_count: int
) -> dict[int, list[PickedParagraph]]:
    """Each paper's picks: its densest paragraphs, then maybe a broad one."""
    picks: dict[int, list[PickedParagraph]] = {}
    for paper_id, paragraphs in score_paragraphs(hits, weights).items():
        dense = densest(paragraphs, dense_count)
        chosen = [PickedParagraph(paper_id, p.chunk_id, DENSITY_REASON) for p in dense]
        broad = broadest(paragraphs, dense, weights)
        if broad is not None:
            chosen.append(PickedParagraph(paper_id, broad.chunk_id, BREADTH_REASON))
        picks[paper_id] = chosen
    return picks


def densest(paragraphs: Sequence[ParagraphScore], count: int) -> list[ParagraphScore]:
    """The `count` paragraphs with the most hits; earlier chunks win ties."""
    if count <= 0:
        return []
    return sorted(paragraphs, key=lambda p: (-p.density, p.chunk_id))[:count]


def broadest(
    paragraphs: Sequence[ParagraphScore],
    already: Sequence[ParagraphScore],
    weights: Sequence[float],
) -> ParagraphScore | None:
    """The broadest paragraph not yet picked, if it beats the picks' breadth."""
    taken = {p.chunk_id for p in already}
    remaining = [p for p in paragraphs if p.chunk_id not in taken]
    if not remaining:
        return None
    best = min(remaining, key=lambda p: (-p.terms_matched, -breadth_score(p, weights), p.chunk_id))
    floor = max((p.terms_matched for p in already), default=0)
    return best if best.terms_matched > floor else None


def breadth_score(paragraph: ParagraphScore, weights: Sequence[float]) -> float:
    """Σ IDF × ln(1 + hits) over the terms the paragraph matched."""
    return sum(
        weights[term_index] * math.log(1 + hits)
        for term_index, hits in paragraph.term_hits.items()
    )
