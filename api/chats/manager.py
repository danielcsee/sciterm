"""Database manager for saved chats."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth import Principal
from api.chats import queries
from api.chats.schemas import (
    ChatTurnCreate,
    StartChatRequest,
    SavedChatMessage,
    SavedChatOut,
    SavedChatSummary,
    SavedCitation,
    SavedEntityPill,
)
from api.annotations.schemas import AnnotationSource, UserAnnotationOut
from api.llm.models import AnswerEntity

if TYPE_CHECKING:
    from api.corpus.models import RagSearchResponse


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
        annotations = [
            _annotation_from_row(row)
            for row in self._session.execute(
                text(queries.GET_ANNOTATIONS_SQL), {"chat_id": chat_id}
            )
        ]
        messages = [
            _message_from_row(row, citations.get(row.id, []), entities.get(row.id, []))
            for row in message_rows
        ]
        return SavedChatOut(
            chat_id=chat.chat_id,
            title=chat.title,
            messages=messages,
            annotations=annotations,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    def start(self, body: StartChatRequest) -> SavedChatOut:
        title = body.content[:20]
        chat_id = self._session.execute(
            text(queries.INSERT_CHAT_SQL),
            {"title": title, **self._owner.params()},
        ).scalar_one()
        self._insert_turn(chat_id, 0, body)
        return self._require_read_back(chat_id)

    def append_turn(self, chat_id: int, body: ChatTurnCreate) -> Optional[SavedChatOut]:
        found = self._session.execute(
            text(queries.LOCK_CHAT_SQL), {"chat_id": chat_id, **self._owner.params()}
        ).scalar_one_or_none()
        if found is None:
            return None
        ordinal = self._session.execute(
            text(queries.NEXT_MESSAGE_ORDINAL_SQL), {"chat_id": chat_id}
        ).scalar_one()
        self._insert_turn(chat_id, ordinal, body)
        self._session.execute(text(queries.UPDATE_CHAT_TOUCHED_SQL), {"chat_id": chat_id})
        return self._require_read_back(chat_id)

    def save_result(
        self, chat_id: int, message_id: UUID, result: RagSearchResponse
    ) -> bool:
        analysis = result.analysis
        response_kind = result.intent.tool if result.intent else (
            "paper_search" if result.search_method else None
        )
        fallback = _intent_text(result)
        updated = self._session.execute(
            text(queries.UPDATE_MESSAGE_RESULT_SQL),
            {
                "chat_id": chat_id,
                "message_id": str(message_id),
                "content": analysis.answer if analysis and analysis.answer else fallback,
                "fallback_text": fallback if analysis else None,
                "response_kind": response_kind,
                "result_papers": json.dumps(
                    [paper.model_dump(mode="json") for paper in result.papers]
                ),
                "papers_considered": result.papers_considered,
                "analysis_entity_ids": json.dumps(analysis.entity_ids if analysis else []),
                "analysis_duplicates_rejected": (
                    analysis.duplicates_rejected if analysis else 0
                ),
                "analysis_model": analysis.model if analysis else None,
                "analysis_error": analysis.error if analysis else None,
                **self._owner.params(),
            },
        ).scalar_one_or_none()
        if updated is None:
            return False
        self._session.execute(
            text(queries.DELETE_CITATIONS_SQL), {"message_id": str(message_id)}
        )
        if analysis:
            papers = {paper.paper_id: paper for paper in result.papers}
            for position, citation in enumerate(analysis.citations):
                paper = papers.get(citation.paper_id)
                self._insert_citation(message_id, citation, position, paper)
        self._touch(chat_id)
        return True

    def save_answer(
        self,
        chat_id: int,
        message_id: UUID,
        answer: Optional[str],
        model: Optional[str],
        error: Optional[str],
    ) -> bool:
        updated = self._session.execute(
            text(queries.UPDATE_MESSAGE_ANSWER_SQL),
            {
                "chat_id": chat_id,
                "message_id": str(message_id),
                "answer": answer,
                "model": model,
                "error": error,
                **self._owner.params(),
            },
        ).scalar_one_or_none()
        if updated is not None:
            self._touch(chat_id)
        return updated is not None

    def save_entities(
        self, chat_id: int, message_id: UUID, entities: list[AnswerEntity]
    ) -> bool:
        if not self._message_owned(chat_id, message_id):
            return False
        self._session.execute(
            text(queries.DELETE_ENTITIES_SQL), {"message_id": str(message_id)}
        )
        for position, entity in enumerate(entities):
            self._insert_entity(message_id, entity, position)
        self._touch(chat_id)
        return True

    def fail_message(self, chat_id: int, message_id: UUID, error: str) -> bool:
        updated = self._session.execute(
            text(queries.FAIL_MESSAGE_SQL),
            {
                "chat_id": chat_id,
                "message_id": str(message_id),
                "error": error,
                **self._owner.params(),
            },
        ).scalar_one_or_none()
        if updated is not None:
            self._touch(chat_id)
        return updated is not None

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

    def _insert_turn(self, chat_id: int, ordinal: int, turn: ChatTurnCreate) -> None:
        for offset, values in enumerate(
            (
                (turn.user_message_id, "user", turn.content, "done"),
                (turn.assistant_message_id, "assistant", "Searching your corpus…", "pending"),
            )
        ):
            message_id, role, content, status = values
            self._session.execute(
                text(queries.INSERT_MESSAGE_SQL),
                {
                    "id": str(message_id),
                    "chat_id": chat_id,
                    "ordinal": ordinal + offset,
                    "role": role,
                    "content": content,
                    "fallback_text": None,
                    "status": status,
                    "response_kind": None,
                    "result_papers": "[]",
                    "papers_considered": 0,
                    "analysis_entity_ids": "[]",
                    "analysis_duplicates_rejected": 0,
                    "analysis_model": None,
                    "analysis_error": None,
                },
            )

    def _insert_entity(self, message_id: UUID, entity: object, position: int) -> None:
        self._session.execute(
            text(queries.INSERT_ENTITY_SQL),
            {
                "message_id": str(message_id),
                "position": position,
                "entity_id": entity.entity_id,
                "identifier": entity.identifier,
                "entity_type": entity.entity_type,
                "name": entity.name,
                "phrases": json.dumps(entity.phrases),
            },
        )

    def _insert_citation(
        self, message_id: UUID, citation: object, position: int, paper: object | None
    ) -> None:
        self._session.execute(
            text(queries.INSERT_CITATION_SQL),
            {
                "message_id": str(message_id),
                "number": citation.number,
                "position": position,
                "paper_id": citation.paper_id,
                "chunk_id": citation.chunk_id,
                "paper_chunk_ordinal": citation.ordinal,
                "paper_pmid": paper.pmid if paper else None,
                "paper_title": paper.title if paper else None,
                "section_type": citation.section_type,
                "quoted_text": citation.text,
                "selected_by": citation.selected_by,
            },
        )

    def _message_owned(self, chat_id: int, message_id: UUID) -> bool:
        return (
            self._session.execute(
                text(queries.CHAT_MESSAGE_OWNED_SQL),
                {
                    "chat_id": chat_id,
                    "message_id": str(message_id),
                    **self._owner.params(),
                },
            ).scalar_one_or_none()
            is not None
        )

    def _touch(self, chat_id: int) -> None:
        self._session.execute(text(queries.UPDATE_CHAT_TOUCHED_SQL), {"chat_id": chat_id})

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


def _annotation_from_row(row: object) -> UserAnnotationOut:
    return UserAnnotationOut(
        id=row.id,
        phrase=row.phrase,
        surrounding_context=row.surrounding_context,
        definition=row.definition,
        source=AnnotationSource(
            chat_id=row.ai_chat_id,
            chat_message_id=row.ai_chat_message_id,
            paper_id=row.paper_id,
            paper_chunk_ordinal=row.paper_chunk_ordinal,
            source_key=row.source_key,
            quote_exact=row.quote_exact,
            quote_prefix=row.quote_prefix,
            quote_suffix=row.quote_suffix,
            start_offset=row.start_offset,
            end_offset=row.end_offset,
        ),
        position=row.position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _intent_text(result: RagSearchResponse) -> str:
    analysis = result.analysis
    if analysis and analysis.error and not analysis.answer:
        return f"Could not write an answer: {analysis.error}"
    if result.intent:
        return f"Tool: {result.intent.tool}"
    return f"Tool: none ({result.intent_error or 'intent routing did not run'})"
