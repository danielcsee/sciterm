"""`api.paper_analysis.selection` — paragraph scoring and per-paper picks."""

from __future__ import annotations

import math

from api.paper_analysis.models import ParagraphHit, ParagraphScore, PickedParagraph
from api.paper_analysis.selection import (
    BREADTH_REASON,
    DENSITY_REASON,
    breadth_score,
    broadest,
    densest,
    score_paragraphs,
    select_paragraphs,
)


def _para(chunk_id: int, term_hits: dict[int, float], paper_id: int = 1) -> ParagraphScore:
    return ParagraphScore(paper_id, chunk_id, dict(term_hits))


def test_score_paragraphs() -> None:
    cases = [
        {"hits": [], "weights": [1.0], "expected": {}},
        {
            # Two papers; paragraph 10 matches both terms.
            "hits": [
                ParagraphHit(1, 10, 0, 3),
                ParagraphHit(1, 10, 1, 1),
                ParagraphHit(1, 11, 0, 2),
                ParagraphHit(2, 20, 1, 4),
            ],
            "weights": [1.0, 2.0],
            "expected": {1: {10: {0: 3, 1: 1}, 11: {0: 2}}, 2: {20: {1: 4}}},
        },
        {
            # A zero-weight (dropped) term and a zero rank are both ignored.
            "hits": [ParagraphHit(1, 10, 0, 3), ParagraphHit(1, 10, 1, 5), ParagraphHit(1, 11, 0, 0)],
            "weights": [1.0, 0.0],
            "expected": {1: {10: {0: 3}}},
        },
        {
            # Repeat hits for one (paragraph, term) add up: synonyms of one term.
            "hits": [ParagraphHit(1, 10, 0, 2), ParagraphHit(1, 10, 0, 1)],
            "weights": [1.0],
            "expected": {1: {10: {0: 3}}},
        },
    ]
    for case in cases:
        scored = score_paragraphs(case["hits"], case["weights"])
        actual = {
            paper_id: {p.chunk_id: p.term_hits for p in paragraphs}
            for paper_id, paragraphs in scored.items()
        }
        assert actual == case["expected"]


def test_densest() -> None:
    paragraphs = [_para(12, {0: 2}), _para(10, {0: 1, 1: 4}), _para(11, {0: 2}), _para(13, {1: 1})]
    cases = [
        {"count": 2, "expected": [10, 11]},  # 5 hits, then 11 beats 12 on the tie
        {"count": 3, "expected": [10, 11, 12]},
        {"count": 10, "expected": [10, 11, 12, 13]},
        {"count": 0, "expected": []},
        {"count": -1, "expected": []},
    ]
    for case in cases:
        actual = [p.chunk_id for p in densest(paragraphs, case["count"])]
        assert actual == case["expected"]


def test_breadth_score() -> None:
    weights = [2.0, 0.5, 0.0]
    cases = [
        {"term_hits": {}, "expected": 0.0},
        {"term_hits": {0: 1}, "expected": 2.0 * math.log(2)},
        {"term_hits": {0: 3, 1: 1}, "expected": 2.0 * math.log(4) + 0.5 * math.log(2)},
        {"term_hits": {2: 9}, "expected": 0.0},
    ]
    for case in cases:
        assert math.isclose(
            breadth_score(_para(1, case["term_hits"]), weights), case["expected"], abs_tol=1e-9
        )


def test_broadest() -> None:
    weights = [1.0, 3.0, 1.0]
    one_term = _para(1, {0: 9})
    two_terms_common = _para(2, {0: 1, 2: 1})
    two_terms_rare = _para(3, {0: 1, 1: 1})
    three_terms = _para(4, {0: 1, 1: 1, 2: 1})
    cases = [
        # Beats a one-term dense pick by matching two; the rarer term wins the tie.
        {
            "paragraphs": [one_term, two_terms_common, two_terms_rare],
            "already": [one_term],
            "expected": 3,
        },
        # No wider than the widest pick: adds nothing.
        {
            "paragraphs": [two_terms_rare, two_terms_common],
            "already": [two_terms_rare],
            "expected": None,
        },
        # Every paragraph already picked.
        {"paragraphs": [one_term], "already": [one_term], "expected": None},
        # Nothing picked yet: any matched paragraph is broader than none.
        {"paragraphs": [one_term, three_terms], "already": [], "expected": 4},
    ]
    for case in cases:
        best = broadest(case["paragraphs"], case["already"], weights)
        assert (best.chunk_id if best else None) == case["expected"]


def test_select_paragraphs() -> None:
    weights = [1.0, 2.0]
    cases = [
        {"hits": [], "dense_count": 2, "expected": {}},
        {
            # Paper 1: the two densest match only term 0, so the one paragraph
            # matching both terms is added for breadth. Paper 2: its dense pick
            # already matches both, so no breadth pick.
            "hits": [
                ParagraphHit(1, 10, 0, 5),
                ParagraphHit(1, 11, 0, 4),
                ParagraphHit(1, 12, 0, 1),
                ParagraphHit(1, 12, 1, 1),
                ParagraphHit(2, 20, 0, 2),
                ParagraphHit(2, 20, 1, 2),
                ParagraphHit(2, 21, 0, 1),
            ],
            "dense_count": 2,
            "expected": {
                1: [
                    PickedParagraph(1, 10, DENSITY_REASON),
                    PickedParagraph(1, 11, DENSITY_REASON),
                    PickedParagraph(1, 12, BREADTH_REASON),
                ],
                2: [PickedParagraph(2, 20, DENSITY_REASON), PickedParagraph(2, 21, DENSITY_REASON)],
            },
        },
        {
            # No dense picks at all: only the breadth pick remains.
            "hits": [ParagraphHit(1, 10, 0, 1)],
            "dense_count": 0,
            "expected": {1: [PickedParagraph(1, 10, BREADTH_REASON)]},
        },
    ]
    for case in cases:
        assert select_paragraphs(case["hits"], weights, case["dense_count"]) == case["expected"]
