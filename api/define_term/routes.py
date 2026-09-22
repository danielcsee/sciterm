"""POST /define: a plain-language definition of a highlighted phrase.

Sync (`def`): the OpenAI client blocks, so FastAPI runs this in its threadpool
rather than stalling the event loop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from api.annotations.manager import AnnotationManager, AnnotationOwner, AnnotationSourceError
from api.annotations.schemas import AnnotationCreate, UserAnnotationOut
from api.auth import Principal, require_user
from api.chats.manager import MissingChatOwnerError, owner_for_principal
from api.db import session_scope
from api.define_term.models import DefineTermRequest, DefineTermResponse
from api.llm import LlmError, define_term, get_llm_client

log = logging.getLogger(__name__)

#: Every call spends OpenAI tokens, so the whole router is gated.
router = APIRouter(tags=["define"], dependencies=[Depends(require_user)])


@router.post("/define", response_model=DefineTermResponse, summary="Define a highlighted phrase")
def define(
    request: DefineTermRequest, principal: Principal = Depends(require_user)
) -> DefineTermResponse:
    """Define `phrase` in simpler language, read in its `surrounding_context`.

    The annotation is committed before OpenAI is asked, so a reload mid-request
    (or a failed definition) still finds it. 503 when no OpenAI key is
    configured; 502 when OpenAI fails or says nothing.
    """
    client = get_llm_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Definitions need an OpenAI key.")
    annotation = (
        _save_annotation(request.annotation, principal)
        if request.annotation is not None
        else None
    )
    try:
        definition = define_term(client, request.phrase, request.surrounding_context)
    except LlmError as exc:
        log.warning("define failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not get a definition.") from exc
    if annotation is not None:
        annotation = _save_definition(annotation, definition, principal)
    return DefineTermResponse(definition=definition, annotation=annotation)


def _save_annotation(request: AnnotationCreate, principal: Principal) -> UserAnnotationOut:
    try:
        with session_scope() as session:
            return AnnotationManager(session, _owner(session, principal)).create(request)
    except AnnotationSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _save_definition(
    annotation: UserAnnotationOut, definition: str, principal: Principal
) -> UserAnnotationOut:
    with session_scope() as session:
        manager = AnnotationManager(session, _owner(session, principal))
        return manager.set_definition(annotation, definition)


def _owner(session: Session, principal: Principal) -> AnnotationOwner:
    try:
        return owner_for_principal(session, principal)
    except MissingChatOwnerError as exc:
        raise HTTPException(status_code=401, detail="annotation owner is unavailable") from exc
