"""`api.paper_search.terms` — confirmed entities or noun phrases become terms."""

from __future__ import annotations

from api.entity_matching import QueryFragment
from api.llm.models import IntentEntity
from api.paper_search.models import SearchTerm
from api.paper_search.terms import entity_terms, noun_phrase_terms


def _entity(entity_id: int, phrase: str) -> IntentEntity:
    return IntentEntity(
        entity_id=entity_id,
        identifier=f"MESH:D{entity_id}",
        entity_type="Disease",
        name=phrase,
        phrase=phrase,
    )


def test_entity_terms() -> None:
    cases = [
        {"entities": [], "expected": []},
        {
            "entities": [
                _entity(1, "CKD"),
                _entity(2, "cats"),
                _entity(3, "ckd"),  # same phrase, another entity: one term
                _entity(1, "CKD"),  # repeated id collapses
            ],
            "expected": [SearchTerm("CKD", (1, 3)), SearchTerm("cats", (2,))],
        },
    ]
    for case in cases:
        assert entity_terms(case["entities"]) == case["expected"], case


def test_noun_phrase_terms() -> None:
    cases = [
        {
            "fragments": [
                QueryFragment("the papers", "noun_phrase"),  # request noun + stop word
                QueryFragment("I", "noun_phrase"),  # stop word only
                QueryFragment("sleep apnea", "noun_phrase"),
                QueryFragment("Sleep Apnea", "noun_phrase"),  # duplicate, other case
                QueryFragment("about sleep apnea", "three_gram"),  # not a noun phrase
                QueryFragment("recent studies", "noun_phrase"),  # one topical word
            ],
            "expected": [SearchTerm("sleep apnea"), SearchTerm("recent studies")],
        },
        {"fragments": [], "expected": []},
    ]
    for case in cases:
        assert noun_phrase_terms(case["fragments"]) == case["expected"], case
