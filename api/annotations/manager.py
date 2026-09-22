"""Owner-scoped persistence for highlighted-text definitions."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.annotations import queries
from api.annotations.schemas import (
    AnnotationCreate,
    AnnotationSource,
    UserAnnotationOut,
)


class AnnotationOwner(Protocol):
    def params(self) -> dict[str, int | None]: ...


class AnnotationSourceError(ValueError):
    """The requested chat message or paper source does not exist."""


class AnnotationManager:
    def __init__(self, session: Session, owner: AnnotationOwner) -> None:
        self._session = session
        self._owner = owner

    def create(self, request: AnnotationCreate) -> UserAnnotationOut:
        """Save the annotation now; its definition is filled in by `set_definition`."""
        chunk_id = self._resolve_source(request.source)
        params = self._params(request, chunk_id)
        params["position"] = self._session.execute(
            text(queries.NEXT_POSITION_SQL), params
        ).scalar_one()
        timestamps = self._session.execute(
            text(queries.INSERT_ANNOTATION_SQL), params
        ).one()
        return UserAnnotationOut(
            **request.model_dump(),
            definition=None,
            position=params["position"],
            created_at=timestamps.created_at,
            updated_at=timestamps.updated_at,
        )

    def set_definition(
        self, annotation: UserAnnotationOut, definition: str
    ) -> UserAnnotationOut:
        updated_at = self._session.execute(
            text(queries.SET_DEFINITION_SQL),
            {"id": str(annotation.id), "definition": definition.strip()},
        ).scalar_one()
        return annotation.model_copy(
            update={"definition": definition.strip(), "updated_at": updated_at}
        )

    def list_for_chat(self, chat_id: int) -> list[UserAnnotationOut]:
        return self._list(chat_id=chat_id, paper_id=None)

    def list_for_paper(self, paper_id: int) -> list[UserAnnotationOut]:
        return self._list(chat_id=None, paper_id=paper_id)

    def delete(self, annotation_id: UUID) -> bool:
        """Remove one of the owner's annotations; False if it is not theirs."""
        deleted = self._session.execute(
            text(queries.DELETE_ANNOTATION_SQL),
            {"id": str(annotation_id), **self._owner.params()},
        ).scalar_one_or_none()
        return deleted is not None

    def _resolve_source(self, source: AnnotationSource) -> int | None:
        owner_params = self._owner.params()
        if source.chat_id is not None:
            found = self._session.execute(
                text(queries.CHAT_SOURCE_SQL),
                {
                    "chat_id": source.chat_id,
                    "message_id": str(source.chat_message_id),
                    **owner_params,
                },
            ).scalar_one_or_none()
            if found is None:
                raise AnnotationSourceError("chat annotation source does not exist")
            return None
        if source.paper_chunk_ordinal is None:
            found = self._session.execute(
                text(queries.PAPER_EXISTS_SQL), {"paper_id": source.paper_id}
            ).scalar_one_or_none()
        else:
            found = self._session.execute(
                text(queries.PAPER_CHUNK_SQL),
                {
                    "paper_id": source.paper_id,
                    "chunk_ordinal": source.paper_chunk_ordinal,
                },
            ).scalar_one_or_none()
        if found is None:
            raise AnnotationSourceError("paper annotation source does not exist")
        return found if source.paper_chunk_ordinal is not None else None

    def _params(
        self, request: AnnotationCreate, chunk_id: int | None
    ) -> dict[str, object]:
        source = request.source
        return {
            "id": str(request.id),
            **self._owner.params(),
            "chat_id": source.chat_id,
            "message_id": str(source.chat_message_id) if source.chat_message_id else None,
            "paper_id": source.paper_id,
            "paper_chunk_id": chunk_id,
            "source_key": source.source_key,
            "phrase": request.phrase.strip(),
            "surrounding_context": request.surrounding_context,
            "quote_exact": source.quote_exact.strip(),
            "quote_prefix": source.quote_prefix,
            "quote_suffix": source.quote_suffix,
            "start_offset": source.start_offset,
            "end_offset": source.end_offset,
        }

    def _list(self, chat_id: int | None, paper_id: int | None) -> list[UserAnnotationOut]:
        rows = self._session.execute(
            text(queries.LIST_ANNOTATIONS_SQL),
            {
                "chat_id": chat_id,
                "paper_id": paper_id,
                **self._owner.params(),
            },
        )
        return [_annotation_from_row(row) for row in rows]


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
