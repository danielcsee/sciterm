"""Authenticated CRUD routes for saved AI conversations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy.orm import Session

from api.auth import Principal, require_user
from api.chats.manager import ChatManager, MissingChatOwnerError, owner_for_principal
from api.chats.schemas import SaveChatRequest, SavedChatList, SavedChatOut
from api.db import session_scope

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=SavedChatList, summary="List saved AI chats")
def list_chats(principal: Principal = Depends(require_user)) -> SavedChatList:
    with session_scope() as session:
        manager = ChatManager(session, _owner(session, principal))
        return SavedChatList(chats=manager.list_chats())


@router.post(
    "", response_model=SavedChatOut, status_code=201, summary="Save an AI chat"
)
def create_chat(
    body: SaveChatRequest, principal: Principal = Depends(require_user)
) -> SavedChatOut:
    with session_scope() as session:
        return ChatManager(session, _owner(session, principal)).create(body)


@router.get("/{chat_id}", response_model=SavedChatOut, summary="Load a saved AI chat")
def get_chat(
    chat_id: int = Path(..., ge=1),
    principal: Principal = Depends(require_user),
) -> SavedChatOut:
    with session_scope() as session:
        chat = ChatManager(session, _owner(session, principal)).get(chat_id)
        if chat is None:
            raise _not_found(chat_id)
        return chat


@router.put("/{chat_id}", response_model=SavedChatOut, summary="Replace a saved AI chat")
def replace_chat(
    body: SaveChatRequest,
    chat_id: int = Path(..., ge=1),
    principal: Principal = Depends(require_user),
) -> SavedChatOut:
    with session_scope() as session:
        chat = ChatManager(session, _owner(session, principal)).replace(chat_id, body)
        if chat is None:
            raise _not_found(chat_id)
        return chat


@router.delete("/{chat_id}", status_code=204, summary="Delete a saved AI chat")
def delete_chat(
    chat_id: int = Path(..., ge=1),
    principal: Principal = Depends(require_user),
) -> Response:
    with session_scope() as session:
        if not ChatManager(session, _owner(session, principal)).delete(chat_id):
            raise _not_found(chat_id)
    return Response(status_code=204)


def _owner(session: Session, principal: Principal):
    try:
        return owner_for_principal(session, principal)
    except MissingChatOwnerError as exc:
        raise HTTPException(
            status_code=401, detail="Your session can no longer save chats."
        ) from exc


def _not_found(chat_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"saved chat {chat_id} does not exist")
