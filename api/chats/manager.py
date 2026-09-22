"""Database manager for saved chats."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth import Principal
from api.chats import queries
from api.chats.schemas import (
    SaveChatRequest,
    SavedChatMessage,
    SavedChatOut,
    SavedChatSummary,
    SavedCitation,
    SavedEntityPill,
)


class MissingChatOwnerError(Exception):
    """The token names no durable auth session from which to derive ownership."""


@dataclass(frozen=True)
class ChatOwner:
    user_id: Optional[int] = None
    free_access_code_id: Optional[int] = None

    def params(self) -> dict[str, Optional[int]]:
        return {
            "owner_user_id": self.user_id,
            "owner_code_id": self.free_access_code_id,
        }


def owner_for_principal(session: Session, principal: Principal) -> ChatOwner:
    """Map admin to its account, free access to its code, and local dev to null."""
    if principal.session_id is None:
        if principal.user_id == 0:
            return ChatOwner()
        raise MissingChatOwnerError()
    if principal.is_admin:
        return ChatOwner(user_id=principal.user_id)
    code_id = session.execute(
        text(queries.AUTH_SESSION_OWNER_SQL), {"session_id": principal.session_id}
    ).scalar_one_or_none()
    if code_id is None:
        raise MissingChatOwnerError()
    return ChatOwner(free_access_code_id=code_id)


class ChatManager:
    def __init__(self, session: Session, owner: ChatOwner) -> None:
        self._session = session
        self._owner = owner

    def list_chats(self) -> list[SavedChatSummary]:
        rows = self._session.execute(
            text(queries.LIST_CHATS_SQL), self._owner.params()
        )
        return [
            SavedChatSummary(
                chat_id=row.chat_id,
                title=row.title,
                message_count=row.message_count,
                preview=row.preview,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def get(self, chat_id: int) -> Optional[SavedChatOut]:
        params = {"chat_id": chat_id, **self._owner.params()}
        chat = self._session.execute(text(queries.GET_CHAT_SQL), params).first()
        if chat is None:
            return None
        message_rows = list(
            self._session.execute(text(queries.GET_MESSAGES_SQL), {"chat_id": chat_id})
        )
        citations, entities = self._children([row.id for row in message_rows])
        messages = [
            _message_from_row(row, citations.get(row.id, []), entities.get(row.id, []))
            for row in message_rows
        ]
        return SavedChatOut(
            chat_id=chat.chat_id,
            title=chat.title,
            messages=messages,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    def create(self, body: SaveChatRequest) -> SavedChatOut:
        chat_id = self._session.execute(
            text(queries.INSERT_CHAT_SQL),
            {"title": body.title, **self._owner.params()},
        ).scalar_one()
        self._insert_messages(chat_id, body.messages)
        return self._require_read_back(chat_id)

    def replace(self, chat_id: int, body: SaveChatRequest) -> Optional[SavedChatOut]:
        updated = self._session.execute(
            text(queries.UPDATE_CHAT_SQL),
            {"chat_id": chat_id, "title": body.title, **self._owner.params()},
        ).scalar_one_or_none()
        if updated is None:
            return None
        self._session.execute(text(queries.DELETE_MESSAGES_SQL), {"chat_id": chat_id})
        self._insert_messages(chat_id, body.messages)
        return self._require_read_back(chat_id)

    def delete(self, chat_id: int) -> bool:
        deleted = self._session.execute(
            text(queries.DELETE_CHAT_SQL),
            {"chat_id": chat_id, **self._owner.params()},
        ).scalar_one_or_none()
        return deleted is not None

    def _children(
        self, message_ids: list[UUID]
    ) -> tuple[dict[UUID, list[SavedCitation]], dict[UUID, list[SavedEntityPill]]]:
        citations: dict[UUID, list[SavedCitation]] = defaultdict(list)
        entities: dict[UUID, list[SavedEntityPill]] = defaultdict(list)
        if not message_ids:
            return citations, entities
        params = {"message_ids": message_ids}
        for row in self._session.execute(text(queries.GET_CITATIONS_SQL), params):
            citations[row.assistant_message_id].append(
                SavedCitation(
                    number=row.number,
                    paper_id=row.paper_id,
                    chunk_id=row.chunk_id,
                    ordinal=row.paper_chunk_ordinal,
                    section_type=row.section_type,
                    text=row.quoted_text,
                    selected_by=row.selected_by,
                    paper_pmid=row.paper_pmid_snapshot,
                    paper_title=row.paper_title_snapshot,
                )
            )
        for row in self._session.execute(text(queries.GET_ENTITIES_SQL), params):
            entities[row.assistant_message_id].append(
                SavedEntityPill(
                    entity_id=row.entity_id,
                    identifier=row.identifier_snapshot,
                    entity_type=row.entity_type_snapshot,
                    name=row.name_snapshot,
                    phrases=row.phrases,
                )
            )
        return citations, entities

    def _insert_messages(self, chat_id: int, messages: list[SavedChatMessage]) -> None:
        for ordinal, message in enumerate(messages):
            self._session.execute(
                text(queries.INSERT_MESSAGE_SQL),
                {
                    "id": str(message.id),
                    "chat_id": chat_id,
                    "ordinal": ordinal,
                    "role": message.role,
                    "content": message.content,
                    "fallback_text": message.fallback_text,
                    "status": message.status,
                    "response_kind": message.response_kind,
                    "result_papers": json.dumps(
                        [paper.model_dump(mode="json") for paper in message.result_papers]
                    ),
                    "papers_considered": message.papers_considered,
                    "analysis_entity_ids": json.dumps(message.analysis_entity_ids),
                    "analysis_duplicates_rejected": message.analysis_duplicates_rejected,
                    "analysis_model": message.analysis_model,
                    "analysis_error": message.analysis_error,
                },
            )
            self._insert_citations(message)
            self._insert_entities(message)

    def _insert_citations(self, message: SavedChatMessage) -> None:
        papers = {paper.paper_id: paper for paper in message.result_papers}
        for position, citation in enumerate(message.citations):
            paper = papers.get(citation.paper_id) if citation.paper_id is not None else None
            self._session.execute(
                text(queries.INSERT_CITATION_SQL),
                {
                    "message_id": str(message.id),
                    "number": citation.number,
                    "position": position,
                    "paper_id": citation.paper_id,
                    "chunk_id": citation.chunk_id,
                    "paper_chunk_ordinal": citation.ordinal,
                    "paper_pmid": citation.paper_pmid or (paper.pmid if paper else None),
                    "paper_title": citation.paper_title or (paper.title if paper else None),
                    "section_type": citation.section_type,
                    "quoted_text": citation.text,
                    "selected_by": citation.selected_by,
                },
            )

    def _insert_entities(self, message: SavedChatMessage) -> None:
        for position, entity in enumerate(message.entity_pills):
            self._session.execute(
                text(queries.INSERT_ENTITY_SQL),
                {
                    "message_id": str(message.id),
                    "position": position,
                    "entity_id": entity.entity_id,
                    "identifier": entity.identifier,
                    "entity_type": entity.entity_type,
                    "name": entity.name,
                    "phrases": json.dumps(entity.phrases),
                },
            )

    def _require_read_back(self, chat_id: int) -> SavedChatOut:
        chat = self.get(chat_id)
        if chat is None:
            raise RuntimeError(f"chat {chat_id} disappeared during its transaction")
        return chat


def _message_from_row(
    row: object,
    citations: list[SavedCitation],
    entities: list[SavedEntityPill],
) -> SavedChatMessage:
    return SavedChatMessage(
        id=row.id,
        role=row.role,
        content=row.content,
        fallback_text=row.fallback_text,
        status=row.status,
        response_kind=row.response_kind,
        result_papers=row.result_papers,
        papers_considered=row.papers_considered,
        analysis_entity_ids=row.analysis_entity_ids,
        analysis_duplicates_rejected=row.analysis_duplicates_rejected,
        analysis_model=row.analysis_model,
        analysis_error=row.analysis_error,
        citations=citations,
        entity_pills=entities,
    )
