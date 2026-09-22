"""`api.llm.answer_entities.resolve_answer_entities` — joining the model's
entities back to candidates, keeping only phrases the answer contains."""

from __future__ import annotations

from api.entity_matching.models import FilteredEntityMatch
from api.llm.answer_entities import AnswerEntities, NamedEntity, resolve_answer_entities

ANSWER = "BRCA1 staining was nuclear [1]; the Brca1 protein ran at 220 kDa [2]."


def _candidate(entity_id: int, name: str) -> list[FilteredEntityMatch]:
    return [
        FilteredEntityMatch(
            entity_id=entity_id,
            identifier=f"GENE:{entity_id}",
            entity_type="Gene",
            database="ncbi",
            name=name,
            matched_text=name,
            score=1.0,
            query_fragment=name,
        )
    ]


CANDIDATES = {31: _candidate(31, "BRCA1"), 32: _candidate(32, "BRCA2")}


def _resolve(named: list[NamedEntity]) -> dict[int, list[str]]:
    resolved = resolve_answer_entities(AnswerEntities(entities=named), CANDIDATES, ANSWER)
    return {entity.entity_id: entity.phrases for entity in resolved}


def test_resolve_answer_entities() -> None:
    cases = [
        # Every phrase kept as written; matching the answer ignores case.
        {
            "named": [NamedEntity(entity_id=31, phrases=["BRCA1", "Brca1 protein"])],
            "expected": {31: ["BRCA1", "Brca1 protein"]},
        },
        # A phrase the answer does not contain is dropped, and so is an
        # entity left with none.
        {
            "named": [
                NamedEntity(entity_id=31, phrases=["BRCA1", "breast cancer gene"]),
                NamedEntity(entity_id=32, phrases=["BRCA2"]),
            ],
            "expected": {31: ["BRCA1"]},
        },
        # An invented id is dropped; a repeated entity merges, deduped by case.
        {
            "named": [
                NamedEntity(entity_id=99, phrases=["BRCA1"]),
                NamedEntity(entity_id=31, phrases=["BRCA1"]),
                NamedEntity(entity_id=31, phrases=["brca1", " Brca1 protein "]),
            ],
            "expected": {31: ["BRCA1", "Brca1 protein"]},
        },
        {"named": [], "expected": {}},
    ]
    for case in cases:
        assert _resolve(case["named"]) == case["expected"], case
