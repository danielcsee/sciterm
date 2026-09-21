"""Tool definitions the model chooses between to route a chat query.

Each tool's Pydantic model is the single source of truth for its arguments:
`openai.pydantic_function_tool` turns it into a strict JSON schema, and the SDK
parses the model's arguments back into the same class.

Every tool carries `entities`, so the model resolves candidates in the same
call that picks the intent rather than in a second round-trip.
"""

from __future__ import annotations

from typing import Literal

import openai
from openai.types.chat import ChatCompletionFunctionToolParam
from pydantic import BaseModel, Field

IntentToolName = Literal["paper_search", "paper_analysis", "no_match"]


class ResolvedEntity(BaseModel):
    """One candidate entity the model found in the user's query."""

    entity_id: int = Field(description="The `id` of a candidate entity, copied exactly.")
    phrase: str = Field(
        description="The exact phrase from the user's query that refers to this entity."
    )


class IntentArguments(BaseModel):
    """Arguments shared by every routing tool."""

    entities: list[ResolvedEntity] = Field(
        description=(
            "Every candidate entity that the user's query refers to, each paired "
            "with the phrase that refers to it. Empty when none are mentioned."
        )
    )


class PaperSearch(IntentArguments):
    """The user wants a list of papers."""


class PaperAnalysis(IntentArguments):
    """The user wants an explanation drawn from the papers."""


class NoMatch(IntentArguments):
    """The user's intent is neither a paper search nor a paper analysis."""

    reason: str = Field(description="One short sentence on why neither tool fits.")


PAPER_SEARCH_DESCRIPTION = (
    "Find papers. Use when the user wants a list of papers back, e.g. "
    "'Find papers about...', 'Which papers mention...', 'Show me studies on...'."
)
PAPER_ANALYSIS_DESCRIPTION = (
    "Explain what the literature says. Use when the user wants an answer or "
    "synthesis rather than a list, e.g. 'Explain what we know about...', "
    "'What do my papers say about...', 'Tell me about...'."
)
NO_MATCH_DESCRIPTION = (
    "Use only when the query is neither a request for papers nor a question "
    "about their content, or its intent cannot be determined."
)

#: The name the model calls each tool by, mapped to its argument model.
INTENT_TOOL_MODELS: dict[IntentToolName, type[IntentArguments]] = {
    "paper_search": PaperSearch,
    "paper_analysis": PaperAnalysis,
    "no_match": NoMatch,
}

INTENT_TOOLS: list[ChatCompletionFunctionToolParam] = [
    openai.pydantic_function_tool(
        PaperSearch, name="paper_search", description=PAPER_SEARCH_DESCRIPTION
    ),
    openai.pydantic_function_tool(
        PaperAnalysis, name="paper_analysis", description=PAPER_ANALYSIS_DESCRIPTION
    ),
    openai.pydantic_function_tool(NoMatch, name="no_match", description=NO_MATCH_DESCRIPTION),
]
