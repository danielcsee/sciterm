"""`api/define_term/routes.py` — the annotation is saved before OpenAI is asked,
so a reload mid-request or a failed definition still finds it."""

from __future__ import annotations

import contextlib
import uuid
from typing import Iterator

import pytest
from fastapi import HTTPException

from api.annotations.schemas import AnnotationCreate, AnnotationSource
from api.auth import Principal
from api.define_term import routes
from api.define_term.models import DefineTermRequest
from api.llm import LlmError


class FakeManager:
    events: list[str] = []

    def __init__(self, session: object, owner: object) -> None:
        pass

    def create(self, request: AnnotationCreate) -> str:
        FakeManager.events.append("create")
        return "annotation"

    def set_definition(self, annotation: str, definition: str) -> None:
        FakeManager.events.append(f"set:{definition}")


@contextlib.contextmanager
def fake_session() -> Iterator[None]:
    yield None


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    FakeManager.events = []
    monkeypatch.setattr(routes, "AnnotationManager", FakeManager)
    monkeypatch.setattr(routes, "session_scope", fake_session)
    monkeypatch.setattr(routes, "owner_for_principal", lambda session, principal: None)
    monkeypatch.setattr(routes, "get_llm_client", lambda: object())
    monkeypatch.setattr(routes, "DefineTermResponse", lambda **fields: fields)
    return FakeManager.events


def _request() -> DefineTermRequest:
    source = AnnotationSource(paper_id=1, paper_chunk_ordinal=0, source_key="paper:1:chunk:0", quote_exact="myopia")
    annotation = AnnotationCreate(id=uuid.uuid4(), phrase="myopia", source=source)
    return DefineTermRequest(phrase="myopia", annotation=annotation)


def _principal() -> Principal:
    return Principal.__new__(Principal)


def test_annotation_is_saved_before_the_definition(
    events: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def define_term(client: object, phrase: str, context: object) -> str:
        events.append("define")
        return "nearsightedness"

    monkeypatch.setattr(routes, "define_term", define_term)
    routes.define(_request(), _principal())
    assert events == ["create", "define", "set:nearsightedness"]


def test_a_failed_definition_keeps_the_saved_annotation(
    events: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def define_term(client: object, phrase: str, context: object) -> str:
        raise LlmError("down")

    monkeypatch.setattr(routes, "define_term", define_term)
    with pytest.raises(HTTPException) as caught:
        routes.define(_request(), _principal())
    assert caught.value.status_code == 502
    assert events == ["create"]
