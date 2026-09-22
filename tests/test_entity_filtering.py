"""`api.entity_matching.filtering` — raw candidate groups become a short list."""

from __future__ import annotations

from api.entity_matching.cutoffs import MatchCutoffs
from api.entity_matching.filtering import filter_entity_matches
from api.entity_matching.models import EntityMatch, EntityMatchGroup


def _match(text: str, score: float, entity_id: int = 1) -> EntityMatch:
    return EntityMatch(
        entity_id=entity_id,
        identifier=f"MESH:{entity_id}",
        entity_type="Disease",
        database="mesh",
        name=text,
        matched_text=text,
        score=score,
    )


def _group(
    fragment: str, matches: list[EntityMatch], method: str = "trigram"
) -> EntityMatchGroup:
    return EntityMatchGroup(
        query_fragment=fragment,
        extraction_method="noun_phrase",
        match_method=method,
        source="entity_name",
        matches=matches,
    )


LONG_QUERY = "one two three four five six"
CUTOFFS = MatchCutoffs(trigram=0.65, embedding=0.65)


def test_filter_entity_matches() -> None:
    cases = [
        {
            "name": "duplicates across fragments keep the best score",
            "query": LONG_QUERY,
            "groups": [
                _group("a", [_match("Asthma", 0.7, 1)]),
                _group("b", [_match("asthma", 0.9, 2)]),
            ],
            "expected": {("trigram", "a"): [], ("trigram", "b"): [("asthma", 2)]},
        },
        {
            "name": "top five per strategy, best first",
            "query": LONG_QUERY,
            "groups": [
                _group("f", [_match(f"t{i}", 0.7 + i / 100, i) for i in range(7)]),
            ],
            "expected": {("trigram", "f"): [(f"t{i}", i) for i in (6, 5, 4, 3, 2)]},
        },
        {
            "name": "short query keeps one candidate per word",
            "query": "lung cancer",
            "groups": [
                _group("f", [_match(f"t{i}", 0.9 - i / 100, i) for i in range(4)]),
            ],
            "expected": {("trigram", "f"): [("t0", 0), ("t1", 1)]},
        },
        {
            "name": "scores below 0.65 are rejected after the cut",
            "query": LONG_QUERY,
            "groups": [
                _group("f", [_match("keep", 0.65, 1), _match("drop", 0.649, 2)]),
            ],
            "expected": {("trigram", "f"): [("keep", 1)]},
        },
        {
            "name": "each matcher is held to its own cutoff",
            "query": LONG_QUERY,
            "groups": [
                _group("f", [_match("a", 0.85, 1), _match("b", 0.75, 2)], "trigram"),
                _group("f", [_match("c", 0.75, 3), _match("d", 0.65, 4)], "embedding"),
            ],
            "cutoffs": MatchCutoffs(trigram=0.8, embedding=0.7),
            "expected": {("trigram", "f"): [("a", 1)], ("embedding", "f"): [("c", 3)]},
        },
        {
            "name": "strategies are limited independently",
            "query": "lung",
            "groups": [
                _group("f", [_match("a", 0.9, 1), _match("b", 0.8, 2)], "trigram"),
                _group("f", [_match("c", 0.95, 3), _match("d", 0.7, 4)], "embedding"),
            ],
            "expected": {("trigram", "f"): [("a", 1)], ("embedding", "f"): [("c", 3)]},
        },
    ]

    for case in cases:
        result = filter_entity_matches(
            case["groups"], case["query"], case.get("cutoffs", CUTOFFS)
        )
        actual: dict[tuple[str, str], list[tuple[str, int]]] = {}
        for group in result:
            for match in group.matches:
                actual.setdefault((group.match_method, match.query_fragment), []).append(
                    (match.matched_text, match.entity_id)
                )
        expected = {key: value for key, value in case["expected"].items() if value}
        assert actual == expected, case["name"]


def test_filter_entity_matches_max_per_strategy() -> None:
    text = " ".join(f"w{index}" for index in range(20))
    group = _group("x", [_match(f"m{index}", 0.9, entity_id=index) for index in range(12)])
    cases = [
        {"max_per_strategy": None, "expected": 5},
        {"max_per_strategy": 10, "expected": 10},
        {"max_per_strategy": 20, "expected": 12},
    ]
    for case in cases:
        options = {} if case["max_per_strategy"] is None else {"max_per_strategy": case["max_per_strategy"]}
        (kept,) = filter_entity_matches([group], text, CUTOFFS, **options)
        assert len(kept.matches) == case["expected"], case
