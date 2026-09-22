"""`DELETE /annotations/{id}` — owner-scoped, 404 when nothing was removed."""

from __future__ import annotations

import contextlib
import uuid
from typing import Iterator

import pytest
from fastapi import HTTPException

from api.annotations import routes
from api.auth import Principal


class FakeManager:
    deleted: list[uuid.UUID] = []
    found: bool = True

    def __init__(self, session: object, owner: object) -> None:
        pass

    def delete(self, annotation_id: uuid.UUID) -> bool:
        FakeManager.deleted.append(annotation_id)
        return FakeManager.found


@contextlib.contextmanager
def fake_session() -> Iterator[None]:
    yield None


@pytest.fixture(autouse=True)
def fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeManager.deleted = []
    FakeManager.found = True
    monkeypatch.setattr(routes, "AnnotationManager", FakeManager)
    monkeypatch.setattr(routes, "session_scope", fake_session)
    monkeypatch.setattr(routes, "owner_for_principal", lambda session, principal: None)


def _principal() -> Principal:
    return Principal.__new__(Principal)


def test_delete_removes_the_annotation() -> None:
    annotation_id = uuid.uuid4()
    response = routes.delete_annotation(annotation_id, _principal())
    assert response.status_code == 204
    assert FakeManager.deleted == [annotation_id]


def test_delete_of_another_owners_annotation_is_not_found() -> None:
    FakeManager.found = False
    with pytest.raises(HTTPException) as caught:
        routes.delete_annotation(uuid.uuid4(), _principal())
    assert caught.value.status_code == 404
