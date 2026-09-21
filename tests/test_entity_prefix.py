"""`api.entity_matching.prefix` — typo-tolerant prefix matching for the type-ahead."""

from __future__ import annotations

import pytest

from api.entity_matching.prefix import (
    PrefixHit,
    allowed_edits,
    first_letter_pattern,
    prefix_edit_distance,
    rank_prefix_hits,
    within_tolerance,
)


def _hit(entity_id: int, text: str, distance: int, mentions: int) -> PrefixHit:
    return PrefixHit(
        entity_id=entity_id,
        identifier=f"ncbi_gene:{entity_id}",
        entity_type="Gene",
        database="ncbi_gene",
        name=text,
        matched_text=text,
        distance=distance,
        mentions=mentions,
    )


def test_allowed_edits() -> None:
    cases = [
        {"name": "empty", "query": "", "expected": 0},
        {"name": "two characters", "query": "ab", "expected": 0},
        {"name": "whitespace is not length", "query": "  ab  ", "expected": 0},
        {"name": "three characters", "query": "abc", "expected": 1},
        {"name": "five characters", "query": "abcde", "expected": 1},
        {"name": "six characters", "query": "abcdef", "expected": 2},
        {"name": "long word", "query": "osteoperosis", "expected": 2},
    ]

    for case in cases:
        assert allowed_edits(case["query"]) == case["expected"], case["name"]


def test_first_letter_pattern() -> None:
    cases = [
        {"name": "lower-cased", "query": "Brac", "expected": "b%"},
        {"name": "leading space skipped", "query": "  tp53", "expected": "t%"},
        {"name": "percent escaped", "query": "%x", "expected": "\\%%"},
        {"name": "underscore escaped", "query": "_x", "expected": "\\_%"},
        {"name": "backslash escaped", "query": "\\x", "expected": "\\\\%"},
        {"name": "empty", "query": "", "expected": None},
        {"name": "blank", "query": "   ", "expected": None},
    ]

    for case in cases:
        assert first_letter_pattern(case["query"]) == case["expected"], case["name"]


def test_prefix_edit_distance() -> None:
    cases = [
        {"name": "exact prefix", "query": "osteop", "text": "Osteoporosis", "expected": 0},
        {"name": "whole text", "query": "brca1", "text": "BRCA1", "expected": 0},
        {"name": "swap at the end", "query": "brac", "text": "BRCA1", "expected": 1},
        {"name": "swap in the middle", "query": "bcra", "text": "BRCA1", "expected": 1},
        {"name": "swap of digits", "query": "tp35", "text": "TP53", "expected": 1},
        {"name": "two swaps", "query": "rbac", "text": "BRCA1", "expected": 2},
        {"name": "substitution", "query": "brcb", "text": "BRCA1", "expected": 1},
        {"name": "missing letter", "query": "catarct", "text": "Cataract", "expected": 1},
        {"name": "extra letter", "query": "brcaa", "text": "BRCA1", "expected": 1},
        {"name": "input longer than text", "query": "brca12", "text": "BRCA1", "expected": 1},
        {"name": "nothing shared", "query": "xyz", "text": "BRCA1", "expected": 3},
        {"name": "empty input", "query": "", "text": "BRCA1", "expected": 0},
    ]

    for case in cases:
        actual = prefix_edit_distance(case["query"], case["text"])
        assert actual == case["expected"], case["name"]


def test_within_tolerance() -> None:
    cases = [
        {
            "name": "one edit allowed at four characters",
            "query": "brac",
            "texts": ["BRCA1", "Bradycardia", "bra", "Breast Neoplasms"],
            "expected": {"BRCA1": 1, "Bradycardia": 1, "bra": 1},
        },
        {
            "name": "a swap is one edit, so it fits a four-character allowance",
            "query": "bcra",
            "texts": ["BRCA1", "Breast Neoplasms"],
            "expected": {"BRCA1": 1},
        },
        {
            "name": "two edits allowed at twelve characters",
            "query": "osteoperosis",
            "texts": ["Osteoporosis", "Osteophyte", "Osteoarthritis"],
            "expected": {"Osteoporosis": 1},
        },
        {
            "name": "a long text is trimmed without changing the result",
            "query": "osteoperosis",
            "texts": ["Osteoporosis, postmenopausal and senile, with fracture"],
            "expected": {"Osteoporosis, postmenopausal and senile, with fracture": 1},
        },
        {
            "name": "no edits allowed at two characters",
            "query": "ab",
            "texts": ["abc", "acb", "b"],
            "expected": {"abc": 0},
        },
        {"name": "no candidates", "query": "brac", "texts": [], "expected": {}},
    ]

    for case in cases:
        assert within_tolerance(case["query"], case["texts"]) == case["expected"], case["name"]


def test_rank_prefix_hits() -> None:
    hits = [
        _hit(2, "BRCA2", 1, 4),
        _hit(3, "Bradycardia", 1, 10),
        _hit(1, "breast cancer 1", 1, 10),
        _hit(1, "BRCA1", 1, 10),
        _hit(5, "Bra", 0, 1),
    ]
    cases = [
        {
            "name": "fewest edits, then most mentions, then shortest; best text per entity",
            "query": "brac",
            "hits": hits,
            "limit": 10,
            "expected": [(5, "Bra", 1.0), (1, "BRCA1", 0.75), (3, "Bradycardia", 0.75), (2, "BRCA2", 0.75)],
        },
        {
            "name": "limit applies after ranking",
            "query": "brac",
            "hits": hits,
            "limit": 2,
            "expected": [(5, "Bra", 1.0), (1, "BRCA1", 0.75)],
        },
        {
            "name": "full tie falls back to alphabetical",
            "query": "brc",
            "hits": [_hit(7, "Brcb", 1, 3), _hit(6, "Brca", 1, 3)],
            "limit": 10,
            "expected": [(6, "Brca", pytest.approx(2 / 3)), (7, "Brcb", pytest.approx(2 / 3))],
        },
        {"name": "no hits", "query": "brac", "hits": [], "limit": 10, "expected": []},
    ]

    for case in cases:
        ranked = rank_prefix_hits(case["query"], case["hits"], case["limit"])
        actual = [(match.entity_id, match.matched_text, match.score) for match in ranked]
        assert actual == case["expected"], case["name"]
