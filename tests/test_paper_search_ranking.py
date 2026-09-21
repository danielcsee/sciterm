"""`api.paper_search.ranking` — IDF weights, scoring, and slot selection."""

from __future__ import annotations

import math

from api.paper_search.models import PaperScore, SearchTerm, TermHit
from api.paper_search.ranking import (
    COVERAGE_REASON,
    RANK_REASON,
    champion_reason,
    common_terms,
    document_frequencies,
    rank,
    score_papers,
    select_papers,
    term_weights,
)

A, B, C = SearchTerm("A", (1,)), SearchTerm("B", (2,)), SearchTerm("C", (3,))


def _paper(paper_id: int, term_hits: dict[int, int], score: float) -> PaperScore:
    return PaperScore(paper_id, dict(term_hits), score)


def test_document_frequencies() -> None:
    cases = [
        {"hits": [], "term_count": 2, "expected": [0, 0]},
        {
            "hits": [TermHit(1, 0, 5), TermHit(2, 0, 1), TermHit(2, 2, 3)],
            "term_count": 3,
            "expected": [2, 0, 1],
        },
    ]
    for case in cases:
        assert document_frequencies(case["hits"], case["term_count"]) == case["expected"]


def test_common_terms() -> None:
    cases = [
        # Above the fraction is dropped; at it is kept.
        {"frequencies": [6, 5, 1], "corpus_size": 10, "max_fraction": 0.5, "expected": {0}},
        # Every matched term is common: the rarest is spared.
        {"frequencies": [9, 7, 8], "corpus_size": 10, "max_fraction": 0.5, "expected": {0, 2}},
        # An unmatched term is never the one spared.
        {"frequencies": [9, 0], "corpus_size": 10, "max_fraction": 0.5, "expected": set()},
        # Ties among the common spare the lowest index.
        {"frequencies": [9, 9], "corpus_size": 10, "max_fraction": 0.5, "expected": {1}},
        {"frequencies": [3], "corpus_size": 0, "max_fraction": 0.5, "expected": set()},
    ]
    for case in cases:
        actual = common_terms(case["frequencies"], case["corpus_size"], case["max_fraction"])
        assert actual == case["expected"], case


def test_term_weights() -> None:
    cases = [
        {
            "frequencies": [2, 0, 5],
            "corpus_size": 10,
            "dropped": set(),
            "expected": [math.log(6), 0.0, math.log(3)],
        },
        {
            "frequencies": [2, 5],
            "corpus_size": 10,
            "dropped": {1},
            "expected": [math.log(6), 0.0],
        },
    ]
    for case in cases:
        actual = term_weights(case["frequencies"], case["corpus_size"], case["dropped"])
        assert actual == case["expected"], case


def test_score_papers() -> None:
    cases = [
        {
            "hits": [TermHit(1, 0, 3), TermHit(1, 1, 1), TermHit(2, 1, 7)],
            "weights": [2.0, 1.0],
            "expected": {
                1: ({0: 3, 1: 1}, 2.0 * math.log(4) + 1.0 * math.log(2)),
                2: ({1: 7}, 1.0 * math.log(8)),
            },
        },
        # Hits on a zero-weight term are ignored; a paper with only those is absent.
        {
            "hits": [TermHit(1, 0, 3), TermHit(1, 1, 4), TermHit(2, 1, 9)],
            "weights": [1.0, 0.0],
            "expected": {1: ({0: 3}, math.log(4))},
        },
    ]
    for case in cases:
        actual = {
            paper.paper_id: (paper.term_hits, paper.score)
            for paper in score_papers(case["hits"], case["weights"])
        }
        assert actual.keys() == case["expected"].keys(), case
        for paper_id, (term_hits, score) in case["expected"].items():
            assert actual[paper_id][0] == term_hits
            assert math.isclose(actual[paper_id][1], score)


def test_rank() -> None:
    cases = [
        {
            "papers": [
                _paper(1, {0: 1}, 9.0),  # one term, high score
                _paper(2, {0: 1, 1: 1}, 1.0),  # two terms beat any score
                _paper(3, {0: 2}, 9.0),  # same terms and score, more mentions
                _paper(4, {0: 2}, 9.0),  # full tie: lower id first
            ],
            "expected": [2, 3, 4, 1],
        },
        {"papers": [], "expected": []},
    ]
    for case in cases:
        assert [paper.paper_id for paper in rank(case["papers"])] == case["expected"]


def test_select_papers() -> None:
    cases = [
        # Coverage, then each term's champion, then the rank fills the rest.
        {
            "papers": [
                _paper(1, {0: 1, 1: 1, 2: 1}, 3.0),
                _paper(2, {0: 50}, 4.0),
                _paper(3, {1: 40}, 3.5),
                _paper(4, {2: 30}, 3.2),
                _paper(5, {0: 2}, 1.0),
                _paper(6, {1: 2}, 0.5),
            ],
            "terms": [A, B, C],
            "weights": [1.0, 2.0, 3.0],
            "top_k": 5,
            "expected": [
                (1, [COVERAGE_REASON]),
                (2, [champion_reason(A)]),
                (3, [champion_reason(B)]),
                (4, [champion_reason(C)]),
                (5, [RANK_REASON]),
            ],
        },
        # A paper winning several slots records every reason and frees a slot.
        {
            "papers": [
                _paper(1, {0: 9, 1: 9}, 5.0),
                _paper(2, {0: 1}, 1.0),
                _paper(3, {1: 1}, 0.5),
            ],
            "terms": [A, B],
            "weights": [1.0, 2.0],
            "top_k": 2,
            "expected": [
                (1, [COVERAGE_REASON, champion_reason(B), champion_reason(A)]),
                (2, [RANK_REASON]),
            ],
        },
        # Slots full: the rarest term's champion gets in, the commoner's does not.
        {
            "papers": [
                _paper(1, {0: 1, 1: 1}, 5.0),
                _paper(2, {0: 50}, 1.0),
                _paper(3, {1: 50}, 1.0),
            ],
            "terms": [A, B],
            "weights": [1.0, 2.0],
            "top_k": 2,
            "expected": [(1, [COVERAGE_REASON]), (3, [champion_reason(B)])],
        },
        # Coverage breaks ties on mentions, not score; output stays in rank order.
        {
            "papers": [_paper(1, {0: 1, 1: 1}, 9.0), _paper(2, {0: 5, 1: 5}, 2.0)],
            "terms": [A, B],
            "weights": [0.0, 0.0],
            "top_k": 2,
            "expected": [(1, [RANK_REASON]), (2, [COVERAGE_REASON])],
        },
        {"papers": [_paper(1, {0: 1}, 1.0)], "terms": [A], "weights": [1.0], "top_k": 0, "expected": []},
        {"papers": [], "terms": [A], "weights": [1.0], "top_k": 5, "expected": []},
    ]
    for case in cases:
        selected = select_papers(case["papers"], case["terms"], case["weights"], case["top_k"])
        actual = [(paper.paper_id, reasons) for paper, reasons in selected]
        assert actual == case["expected"], case
