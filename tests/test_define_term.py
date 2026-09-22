"""`api/define_term/models.py` and `api/llm/definition.py` — the /define request
rules, and what the model is sent."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from api.define_term.models import MAX_PHRASE_CHARS, DefineTermRequest
from api.llm.definition import definition_input


def test_request_strips_the_phrase_and_blanks_empty_context() -> None:
    request = DefineTermRequest(phrase="  hyperaldosteronism ", surrounding_context="   ")
    assert request.phrase == "hyperaldosteronism"
    assert request.surrounding_context is None


def test_request_rejects_unusable_phrases() -> None:
    for phrase in ["", "   ", "x" * (MAX_PHRASE_CHARS + 1)]:
        with pytest.raises(ValidationError):
            DefineTermRequest(phrase=phrase)


def test_definition_input_carries_a_null_context() -> None:
    payload = json.loads(definition_input("renin–angiotensin system", None))
    assert payload == {"phrase": "renin–angiotensin system", "surrounding_context": None}
