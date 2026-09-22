"""Find the entities a generated answer names, and every phrase naming each.

A separate call from intent routing: routing returns one phrase per entity,
because `api.paper_search` turns each distinct phrase into one ranking term.
An answer needs every wording, so it gets its own tool with a phrase list.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence

import openai
from openai.types.chat import ChatCompletionFunctionToolParam
from pydantic import BaseModel, Field

from api.entity_matching.models import EntityStrategyGroup, FilteredEntityMatch
from api.llm.client import LlmClient, LlmError
from api.llm.intent import candidate_entities, candidate_payload, display_name
from api.llm.models import AnswerEntity

log = logging.getLogger(__name__)

ANSWER_ENTITY_INSTRUCTIONS = """\
You find biomedical entities in a passage of text. The input is JSON holding \
the `text` and a list of `candidate_entities`, each with an `id`, a canonical \
`name`, a `type`, and the `matched_text` that surfaced it.

Return every candidate the text actually refers to, with every distinct \
phrase in the text that names it, copied exactly as written there, including \
abbreviations and rewordings. A phrase is the entity's name alone: leave out \
possessives and the words around it, so "BRCA1" from "BRCA1’s role" or \
"BRCA1 band", but "breast cancer" whole. Skip candidates that only resemble \
words in the text but mean something else. Use only the given ids."""

TOOL_NAME = "answer_entities"


class NamedEntity(BaseModel):
    """One candidate entity the model found in the text."""

    entity_id: int = Field(description="The `id` of a candidate entity, copied exactly.")
    phrases: list[str] = Field(
        description="Every phrase in the text that refers to this entity, copied exactly."
    )


class AnswerEntities(BaseModel):
    """The candidate entities the text refers to."""

    entities: list[NamedEntity] = Field(
        description="Every candidate entity the text refers to. Empty when none are."
    )


ANSWER_ENTITY_TOOLS: list[ChatCompletionFunctionToolParam] = [
    openai.pydantic_function_tool(
        AnswerEntities,
        name=TOOL_NAME,
        description="Report the candidate entities the text refers to, with their phrases.",
    )
]


def find_answer_entities(
    client: LlmClient, answer: str, candidate_groups: Sequence[EntityStrategyGroup]
) -> list[AnswerEntity]:
    """The candidates `answer` names, each with the phrases that name it.

    Raises LlmError when the model fails or answers with another tool.
    """
    candidates = candidate_entities(candidate_groups)
    if not candidates:
        return []
    call = client.choose_tool(
        ANSWER_ENTITY_INSTRUCTIONS,
        _answer_input(answer, candidates.values()),
        ANSWER_ENTITY_TOOLS,
    )
    if call.name != TOOL_NAME or not isinstance(call.arguments, AnswerEntities):
        raise LlmError(f"model called an unknown tool {call.name!r}")
    return resolve_answer_entities(call.arguments, candidates, answer)


def resolve_answer_entities(
    arguments: AnswerEntities,
    candidates: dict[int, list[FilteredEntityMatch]],
    answer: str,
) -> list[AnswerEntity]:
    """The model's entities, joined back to their candidates.

    Invented ids are dropped, as are phrases the answer does not contain: an
    underline over nothing is worse than none. An entity left with no phrase
    is dropped too. Repeats of one entity merge.
    """
    by_id: dict[int, AnswerEntity] = {}
    for named in arguments.entities:
        matches = candidates.get(named.entity_id)
        if matches is None:
            log.warning("model returned entity id %d, which was not a candidate", named.entity_id)
            continue
        entity = by_id.setdefault(named.entity_id, _answer_entity(matches[0]))
        _add_phrases(entity, named.phrases, answer)
    return [entity for entity in by_id.values() if entity.phrases]


def _add_phrases(entity: AnswerEntity, phrases: Iterable[str], answer: str) -> None:
    lowered = answer.casefold()
    seen = {phrase.casefold() for phrase in entity.phrases}
    for phrase in phrases:
        text = phrase.strip()
        key = text.casefold()
        if not text or key in seen or key not in lowered:
            continue
        seen.add(key)
        entity.phrases.append(text)


def _answer_input(answer: str, candidates: Iterable[list[FilteredEntityMatch]]) -> str:
    payload = {
        "text": answer,
        "candidate_entities": [candidate_payload(matches) for matches in candidates],
    }
    return json.dumps(payload, ensure_ascii=False)


def _answer_entity(match: FilteredEntityMatch) -> AnswerEntity:
    return AnswerEntity(
        entity_id=match.entity_id,
        identifier=match.identifier,
        entity_type=match.entity_type,
        name=display_name(match),
    )
