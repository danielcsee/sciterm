"""Route a chat query to one tool, resolving its entity candidates on the way."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from typing import Optional, cast

from api.entity_matching.models import EntityStrategyGroup, FilteredEntityMatch
from api.llm.client import LlmClient, LlmError
from api.llm.models import IntentEntity, IntentResult
from api.llm.tools import INTENT_TOOL_MODELS, INTENT_TOOLS, IntentArguments, NoMatch

log = logging.getLogger(__name__)

INTENT_INSTRUCTIONS = """\
You route questions for an app that searches and explains scientific \
literature. The input is JSON holding the user's `query` and a list of \
`candidate_entities`, each with an `id`, a canonical `name`, a `type`, and the \
`matched_text` that surfaced it.

1. Entities: return every candidate the query actually refers to, paired with \
the exact phrase from the query that refers to it. Skip candidates that only \
resemble a word in the query but mean something else. Use only the given ids.
2. Intent: call exactly one tool. Call paper_search when the user wants a list \
of papers, and paper_analysis when they want an explanation or synthesis of \
what papers say. Call no_match only if neither is likely."""


def classify_intent(
    client: LlmClient, query: str, candidate_groups: Sequence[EntityStrategyGroup]
) -> IntentResult:
    """Ask the model which tool fits `query`, and which candidates it names.

    Raises LlmError when the model fails or calls a tool we did not offer.
    """
    candidates = candidate_entities(candidate_groups)
    call = client.choose_tool(
        INTENT_INSTRUCTIONS, _intent_input(query, candidates.values()), INTENT_TOOLS
    )
    if call.name not in INTENT_TOOL_MODELS:
        raise LlmError(f"model called an unknown tool {call.name!r}")
    arguments = cast(IntentArguments, call.arguments)
    return IntentResult(
        tool=call.name,
        entities=resolve_entities(arguments, candidates),
        reason=arguments.reason if isinstance(arguments, NoMatch) else None,
        model=client.model,
    )


def candidate_entities(
    groups: Sequence[EntityStrategyGroup],
) -> dict[int, list[FilteredEntityMatch]]:
    """Every filtered candidate, keyed by entity so each is offered once.

    One entity can surface through several strategies and wordings; all of its
    matches are kept so the model sees every text that pointed at it.
    """
    by_entity: dict[int, list[FilteredEntityMatch]] = {}
    for group in groups:
        for match in group.matches:
            by_entity.setdefault(match.entity_id, []).append(match)
    return by_entity


def resolve_entities(
    arguments: IntentArguments, candidates: dict[int, list[FilteredEntityMatch]]
) -> list[IntentEntity]:
    """The model's entities, joined back to their candidates.

    Ids the model invented are dropped, and each entity is kept once.
    """
    resolved: list[IntentEntity] = []
    seen: set[int] = set()
    for entity in arguments.entities:
        matches = candidates.get(entity.entity_id)
        if matches is None:
            log.warning("model returned entity id %d, which was not a candidate", entity.entity_id)
            continue
        if entity.entity_id in seen:
            continue
        seen.add(entity.entity_id)
        resolved.append(_intent_entity(matches[0], entity.phrase))
    return resolved


def _intent_input(query: str, candidates: Iterable[list[FilteredEntityMatch]]) -> str:
    """The user turn: the query and its candidates, as one JSON document."""
    payload = {
        "query": query,
        "candidate_entities": [candidate_payload(matches) for matches in candidates],
    }
    return json.dumps(payload, ensure_ascii=False)


def candidate_payload(matches: list[FilteredEntityMatch]) -> dict[str, object]:
    """One candidate as the model sees it, with every text that surfaced it."""
    first = matches[0]
    return {
        "id": first.entity_id,
        "name": display_name(first),
        "type": first.entity_type,
        "matched_text": sorted({match.matched_text for match in matches}),
    }


def display_name(match: FilteredEntityMatch) -> Optional[str]:
    return match.name or match.matched_text


def _intent_entity(match: FilteredEntityMatch, phrase: str) -> IntentEntity:
    return IntentEntity(
        entity_id=match.entity_id,
        identifier=match.identifier,
        entity_type=match.entity_type,
        name=display_name(match),
        phrase=phrase,
    )
