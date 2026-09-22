"""`api.paper_analysis.evidence` — ordering, numbering and entity ids."""

from __future__ import annotations

from api.paper_analysis.evidence import number_citations, priority_order, query_entity_ids
from api.paper_analysis.models import PickedParagraph
from api.paper_analysis.selection import BREADTH_REASON, DENSITY_REASON
from api.paper_search import SearchTermSummary


def _pick(paper_id: int, chunk_id: int, reason: str = DENSITY_REASON) -> PickedParagraph:
    return PickedParagraph(paper_id, chunk_id, reason)


def _row(chunk_id: int, paper_id: int, ordinal: int) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "paper_id": paper_id,
        "ordinal": ordinal,
        "section_type": "RESULTS",
        "text": f"paragraph {chunk_id}",
    }


def _term(entity_ids: list[int], weight: float) -> SearchTermSummary:
    return SearchTermSummary(phrase="t", entity_ids=entity_ids, papers_matched=1, weight=weight)


def test_priority_order() -> None:
    picks = {
        1: [_pick(1, 10), _pick(1, 11, BREADTH_REASON)],
        2: [_pick(2, 20)],
    }
    cases = [
        {"paper_ids": [1, 2], "expected": [10, 11, 20]},
        {"paper_ids": [2, 1], "expected": [20, 10, 11]},
        # A paper with no picks is skipped; an unranked paper's picks are not taken.
        {"paper_ids": [3, 2], "expected": [20]},
        {"paper_ids": [], "expected": []},
    ]
    for case in cases:
        actual = [pick.chunk_id for pick in priority_order(case["paper_ids"], picks)]
        assert actual == case["expected"]


def test_number_citations() -> None:
    rows = {10: _row(10, 1, 40), 11: _row(11, 1, 5), 20: _row(20, 2, 7)}
    cases = [
        {"paper_ids": [1], "picks": [], "expected": []},
        {
            # Grouped by paper rank, reading order within a paper, so the
            # breadth pick at ordinal 5 is numbered before the dense one at 40.
            "paper_ids": [2, 1],
            "picks": [_pick(1, 10), _pick(1, 11, BREADTH_REASON), _pick(2, 20)],
            "expected": [
                (1, 20, 7, DENSITY_REASON),
                (2, 11, 5, BREADTH_REASON),
                (3, 10, 40, DENSITY_REASON),
            ],
        },
        {
            # A pick whose row is missing is dropped, and numbering stays dense.
            "paper_ids": [1, 2],
            "picks": [_pick(1, 99), _pick(2, 20)],
            "expected": [(1, 20, 7, DENSITY_REASON)],
        },
    ]
    for case in cases:
        citations = number_citations(case["paper_ids"], case["picks"], rows)
        actual = [(c.number, c.chunk_id, c.ordinal, c.selected_by) for c in citations]
        assert actual == case["expected"]
        for citation in citations:
            assert citation.text == f"paragraph {citation.chunk_id}"
            assert citation.section_type == "RESULTS"


def test_query_entity_ids() -> None:
    cases = [
        {"terms": [], "expected": []},
        {"terms": [_term([3, 4], 1.0), _term([9], 2.0)], "expected": [3, 4, 9]},
        # Dropped (zero-weight) terms contribute nothing; repeats appear once.
        {"terms": [_term([3], 0.0), _term([4, 5], 1.0), _term([5, 6], 1.0)], "expected": [4, 5, 6]},
        # Full-text terms carry no entities.
        {"terms": [_term([], 1.0)], "expected": []},
    ]
    for case in cases:
        assert query_entity_ids(case["terms"]) == case["expected"]
