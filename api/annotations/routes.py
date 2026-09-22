"""Authenticated reads and deletes for annotations; creation occurs through /define."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from api.annotations.manager import AnnotationManager
from api.annotations.schemas import UserAnnotationList
from api.auth import Principal, require_user
from api.chats.manager import MissingChatOwnerError, owner_for_principal
from api.db import session_scope

router = APIRouter(prefix="/annotations", tags=["annotations"])


@router.get("", response_model=UserAnnotationList, summary="List annotations")
def list_annotations(
    chat_id: Optional[int] = Query(None, ge=1),
    paper_id: Optional[int] = Query(None, ge=1),
    principal: Principal = Depends(require_user),
) -> UserAnnotationList:
    if (chat_id is None) == (paper_id is None):
        raise HTTPException(status_code=422, detail="provide exactly one chat_id or paper_id")
    with session_scope() as session:
        manager = _manager(session, principal)
        annotations = (
            manager.list_for_chat(chat_id)
            if chat_id is not None
            else manager.list_for_paper(paper_id)  # type: ignore[arg-type]
        )
        return UserAnnotationList(annotations=annotations)


@router.delete("/{annotation_id}", status_code=204, summary="Delete an annotation")
def delete_annotation(
    annotation_id: UUID = Path(...),
    principal: Principal = Depends(require_user),
) -> Response:
    with session_scope() as session:
        if not _manager(session, principal).delete(annotation_id):
            raise HTTPException(
                status_code=404, detail=f"annotation {annotation_id} does not exist"
            )
    return Response(status_code=204)


def _manager(session: Session, principal: Principal) -> AnnotationManager:
    try:
        owner = owner_for_principal(session, principal)
    except MissingChatOwnerError as exc:
        raise HTTPException(status_code=401, detail="annotation owner is unavailable") from exc
    return AnnotationManager(session, owner)
