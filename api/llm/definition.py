"""Define a phrase a reader highlighted, in simpler language."""

from __future__ import annotations

import json
from typing import Optional

from api.llm.client import LlmClient

DEFINITION_INSTRUCTIONS = """\
Your job is to help a user understand terms and phrases they found in a \
scientific paper. The input is JSON holding the `phrase` they highlighted and \
the `surrounding_context` it appeared in, or null when there is none. Define \
the phrase in simpler language, using the surrounding context (if any) to help \
them understand what it means.

- Explain what the phrase means here, not every sense it can have.
- Unpack jargon and abbreviations; do not define a term with harder terms.
- Be concise: at most 120 words of plain prose, no headings or lists."""


def define_term(client: LlmClient, phrase: str, surrounding_context: Optional[str]) -> str:
    """The model's plain-language definition. Raises LlmError on failure."""
    return client.complete_text(
        DEFINITION_INSTRUCTIONS, definition_input(phrase, surrounding_context)
    )


def definition_input(phrase: str, surrounding_context: Optional[str]) -> str:
    return json.dumps(
        {"phrase": phrase, "surrounding_context": surrounding_context},
        ensure_ascii=False,
    )
