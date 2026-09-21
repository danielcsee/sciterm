"""OpenAI transport: a forced tool call, or a streamed answer, each checked.

Business logic (what to ask, and what the answer means) lives in `intent.py`;
this module only sends the request and validates the shape of what came back.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import openai
from openai.types.chat import ChatCompletionFunctionToolParam
from openai.types.responses import (
    ParsedResponse,
    ParsedResponseFunctionToolCall,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from pydantic import BaseModel

from api.app.config import get_settings

log = logging.getLogger(__name__)


class LlmError(Exception):
    """OpenAI failed, or answered in a shape we cannot use."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: BaseModel


class LlmClient:
    """Holds the OpenAI client and exposes the calls this app makes."""

    def __init__(
        self,
        client: openai.OpenAI,
        *,
        model: str,
        reasoning_effort: Optional[str],
    ) -> None:
        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort

    @property
    def model(self) -> str:
        return self._model

    def choose_tool(
        self,
        instructions: str,
        user_input: str,
        tools: Iterable[ChatCompletionFunctionToolParam],
    ) -> ToolCall:
        """Make the model call exactly one of `tools`, and return that call."""
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=instructions,
                input=user_input,
                tools=list(tools),
                tool_choice="required",
                parallel_tool_calls=False,
                store=False,
                **self._reasoning_options(),
            )
        except openai.OpenAIError as exc:
            raise LlmError(f"OpenAI request failed: {exc}") from exc
        return _single_tool_call(response)

    def stream_text(self, instructions: str, user_input: str, *, timeout: float) -> Iterator[str]:
        """Free-text answer, yielded as the model writes it. No retry.

        Generation takes far longer than routing, so it gets a longer budget —
        and a retry would double a wait the reader is already sitting through.
        The timeout bounds each read, not the whole answer. Raises LlmError,
        possibly after some text has already been yielded.
        """
        try:
            with self._client.with_options(timeout=timeout, max_retries=0).responses.create(
                model=self._model,
                instructions=instructions,
                input=user_input,
                store=False,
                stream=True,
                **self._reasoning_options(),
            ) as stream:
                yield from _text_deltas(stream)
        except openai.OpenAIError as exc:
            raise LlmError(f"OpenAI request failed: {exc}") from exc

    def _reasoning_options(self) -> dict[str, object]:
        if self._reasoning_effort is None:
            return {}
        return {"reasoning": {"effort": self._reasoning_effort}}


def _text_deltas(events: Iterable[ResponseStreamEvent]) -> Iterator[str]:
    """The answer's text as it arrives, or LlmError when the response ends badly."""
    for event in events:
        if isinstance(event, ResponseTextDeltaEvent):
            yield event.delta
        elif isinstance(event, ResponseErrorEvent):
            raise LlmError(f"OpenAI stream failed: {event.message}")
        elif isinstance(event, (ResponseFailedEvent, ResponseIncompleteEvent)):
            raise LlmError(f"OpenAI response ended as {event.response.status}")


def _single_tool_call(response: ParsedResponse[object]) -> ToolCall:
    """The one parsed function call in `response`, or LlmError."""
    calls = [
        item for item in response.output if isinstance(item, ParsedResponseFunctionToolCall)
    ]
    if len(calls) != 1:
        raise LlmError(f"expected exactly one tool call, got {len(calls)}")
    call = calls[0]
    if not isinstance(call.parsed_arguments, BaseModel):
        raise LlmError(f"tool call {call.name!r} carried unparseable arguments")
    return ToolCall(name=call.name, arguments=call.parsed_arguments)


@lru_cache(maxsize=1)
def get_llm_client() -> Optional[LlmClient]:
    """The shared client, or None when no API key is configured."""
    settings = get_settings()
    if settings.openai_api_key is None:
        log.info("OPENAI_API_KEY is unset; chat runs without intent routing")
        return None
    return LlmClient(
        openai.OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.openai_timeout_seconds,
            max_retries=1,
        ),
        model=settings.openai_model,
        reasoning_effort=settings.openai_reasoning_effort,
    )
