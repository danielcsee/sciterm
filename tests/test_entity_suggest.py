"""`api.entity_matching.suggest` — merging type-ahead candidates per entity."""

from __future__ import annotations

from api.entity_matching.models import EntityMatch, EntityMatchGroup
from api.entity_matching.suggest import merge_suggestions


def _match(entity_id: int) -> EntityMatch:
    return EntityMatch(
        entity_id=entity_id,
        identifier=f"MESH:D{entity_id}",
        entity_type="Disease",
        database="ncbi_mesh",
        name=f"Entity {entity_id}",
        matched_text=f"Entity {entity_id}",
        score=0.5,
    )


def _group(method: str, source: str, entity_ids: list[int]) -> EntityMatchGroup:
    return EntityMatchGroup(
        query_fragment="brac",
        extraction_method="noun_phrase",
        match_method=method,
        source=source,
        matches=[_match(entity_id) for entity_id in entity_ids],
    )


def test_merge_suggestions() -> None:
    # Deliberately listed lowest priority first: the merge must reorder them.
    groups = [
        _group("embedding", "mention_surface_text", [40, 41]),
        _group("embedding", "entity_name", [30]),
        _group("trigram", "mention_surface_text", [20, 10]),
        _group("trigram", "entity_name", [10, 11]),
    ]
    cases = [
        {
            "name": "groups follow strategy priority, not input order",
            "groups": groups,
            "prefix": [],
            "limit": 10,
            "expected": [10, 11, 20, 30, 40, 41],
        },
        {
            "name": "prefix matches lead, and an entity keeps its first appearance",
            "groups": groups,
            "prefix": [_match(99), _match(20)],
            "limit": 10,
            "expected": [99, 20, 10, 11, 30, 40, 41],
        },
        {
            "name": "limit",
            "groups": groups,
            "prefix": [_match(99)],
            "limit": 3,
            "expected": [99, 10, 11],
        },
        {"name": "nothing found", "groups": [], "prefix": [], "limit": 10, "expected": []},
    ]

    for case in cases:
        merged = merge_suggestions(case["groups"], case["prefix"], case["limit"])
        assert [match.entity_id for match in merged] == case["expected"], case["name"]
