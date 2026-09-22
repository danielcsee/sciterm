"""POST /define: a plain-language definition of a highlighted phrase.

Sync (`def`): the OpenAI client blocks, so FastAPI runs this in its threadpool
rather than stalling the event loop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_user
from api.define_term.models import DefineTermRequest, DefineTermResponse
from api.llm import LlmError, define_term, get_llm_client

log = logging.getLogger(__name__)

#: Every call spends OpenAI tokens, so the whole router is gated.
router = APIRouter(tags=["define"], dependencies=[Depends(require_user)])


@router.post("/define", response_model=DefineTermResponse, summary="Define a highlighted phrase")
def define(request: DefineTermRequest) -> DefineTermResponse:
    """Define `phrase` in simpler language, read in its `surrounding_context`.

    503 when no OpenAI key is configured; 502 when OpenAI fails or says nothing.
    """
    client = get_llm_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Definitions need an OpenAI key.")
    try:
        definition = define_term(client, request.phrase, request.surrounding_context)
    except LlmError as exc:
        log.warning("define failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not get a definition.") from exc
    return DefineTermResponse(definition=definition)
