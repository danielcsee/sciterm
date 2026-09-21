"""`api.llm.client._text_deltas` — reading the answer out of a response stream."""

from __future__ import annotations

import pytest
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseTextDeltaEvent,
)

from api.llm import LlmError
from api.llm.client import _text_deltas


def _delta(text: str) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent.model_construct(type="response.output_text.delta", delta=text)


def _response(status: str) -> Response:
    return Response.model_construct(status=status)


def test_text_deltas_yields_only_text() -> None:
    events = [
        _delta("Hello"),
        _delta(", world"),
        ResponseCompletedEvent.model_construct(
            type="response.completed", response=_response("completed")
        ),
    ]
    assert list(_text_deltas(events)) == ["Hello", ", world"]


def test_text_deltas_raises_on_a_bad_ending() -> None:
    cases = [
        {
            "event": ResponseErrorEvent.model_construct(type="error", message="overloaded"),
            "match": "overloaded",
        },
        {
            "event": ResponseFailedEvent.model_construct(
                type="response.failed", response=_response("failed")
            ),
            "match": "failed",
        },
        {
            "event": ResponseIncompleteEvent.model_construct(
                type="response.incomplete", response=_response("incomplete")
            ),
            "match": "incomplete",
        },
    ]
    for case in cases:
        received: list[str] = []
        with pytest.raises(LlmError, match=case["match"]):
            for piece in _text_deltas([_delta("so far"), case["event"]]):
                received.append(piece)
        assert received == ["so far"], case
