"""`api.entity_matching.rescoring` — edit-distance scores for trigram candidates."""

from __future__ import annotations

import pytest

from api.entity_matching.models import EntityMatch
from api.entity_matching.rescoring import edit_similarity, rescore_by_edit_distance


def _match(text: str, score: float, entity_id: int) -> EntityMatch:
    return EntityMatch(
        entity_id=entity_id,
        identifier=f"MESH:{entity_id}",
        entity_type="Disease",
        database="mesh",
        name=text,
        matched_text=text,
        score=score,
    )


def test_edit_similarity() -> None:
    cases = [
        {"name": "case is ignored", "left": "osteoporosis", "right": "Osteoporosis", "expected": 1.0},
        {"name": "one substitution", "left": "osteoperosis", "right": "Osteoporosis", "expected": 1 - 1 / 12},
        {"name": "one insertion", "left": "asthama", "right": "asthma", "expected": 1 - 1 / 7},
        {"name": "one deletion", "left": "diabtes", "right": "diabetes", "expected": 1 - 1 / 8},
        {"name": "nothing shared", "left": "abc", "right": "xyz", "expected": 0.0},
        {"name": "both empty", "left": "", "right": "", "expected": 1.0},
        {"name": "one empty", "left": "", "right": "abc", "expected": 0.0},
    ]

    for case in cases:
        forward = edit_similarity(case["left"], case["right"])
        backward = edit_similarity(case["right"], case["left"])
        assert forward == pytest.approx(case["expected"]), case["name"]
        assert backward == pytest.approx(case["expected"]), f"{case['name']} (reversed)"


def test_rescore_by_edit_distance() -> None:
    cases = [
        {
            "name": "a typo outranks a higher trigram score",
            "fragment": "osteoperosis",
            "matches": [_match("Osteophyte", 0.9, 1), _match("Osteoporosis", 0.625, 2)],
            "expected": [(2, 0.916667), (1, 0.5)],
        },
        {
            "name": "no candidates",
            "fragment": "asthma",
            "matches": [],
            "expected": [],
        },
    ]

    for case in cases:
        original_scores = [match.score for match in case["matches"]]
        rescored = rescore_by_edit_distance(case["fragment"], case["matches"])
        actual = [(match.entity_id, match.score) for match in rescored]
        assert actual == case["expected"], case["name"]
        assert [match.score for match in case["matches"]] == original_scores, case["name"]
