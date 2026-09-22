"""Short transactions that persist each server-generated chat artifact."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from api.chats.manager import ChatManager, ChatOwner
from api.db import session_scope

if TYPE_CHECKING:
    from api.corpus.models import AnswerDoneEvent, AnswerEntitiesEvent, RagSearchResponse


class ChatArtifactWriter:
    """Persist one assistant message without holding a connection during LLM work."""

    def __init__(self, chat_id: int, message_id: uuid.UUID, owner: ChatOwner) -> None:
        self._chat_id = chat_id
        self._message_id = message_id
        self._owner = owner

    def exists(self) -> bool:
        with session_scope() as session:
            return ChatManager(session, self._owner)._message_owned(
                self._chat_id, self._message_id
            )

    def save_result(self, result: RagSearchResponse) -> None:
        with session_scope() as session:
            if not ChatManager(session, self._owner).save_result(
                self._chat_id, self._message_id, result
            ):
                raise ValueError("assistant message does not belong to this chat")

    def save_answer(self, event: AnswerDoneEvent) -> None:
        with session_scope() as session:
            if not ChatManager(session, self._owner).save_answer(
                self._chat_id,
                self._message_id,
                event.answer,
                event.model,
                event.error,
            ):
                raise ValueError("assistant message does not belong to this chat")

    def save_entities(self, event: AnswerEntitiesEvent) -> None:
        with session_scope() as session:
            if not ChatManager(session, self._owner).save_entities(
                self._chat_id, self._message_id, event.entities
            ):
                raise ValueError("assistant message does not belong to this chat")

    def fail(self, error: str) -> None:
        with session_scope() as session:
            ChatManager(session, self._owner).fail_message(
                self._chat_id, self._message_id, error
            )
