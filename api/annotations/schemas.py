"""Validated wire types for durable highlighted-text definitions."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from pydantic import BaseModel, Field, model_validator

MAX_SOURCE_KEY_CHARS = 500
MAX_QUOTE_CONTEXT_CHARS = 500
MAX_PHRASE_CHARS = 2_000
MAX_CONTEXT_CHARS = 8_000


class AnnotationSource(BaseModel):
    chat_id: Optional[int] = Field(None, ge=1)
    chat_message_id: Optional[uuid.UUID] = None
    paper_id: Optional[int] = Field(None, ge=1)
    paper_chunk_ordinal: Optional[int] = Field(None, ge=0)
    source_key: str = Field(..., min_length=1, max_length=MAX_SOURCE_KEY_CHARS)
    quote_exact: str = Field(..., min_length=1, max_length=MAX_PHRASE_CHARS)
    quote_prefix: Optional[str] = Field(None, max_length=MAX_QUOTE_CONTEXT_CHARS)
    quote_suffix: Optional[str] = Field(None, max_length=MAX_QUOTE_CONTEXT_CHARS)
    start_offset: Optional[int] = Field(None, ge=0)
    end_offset: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def _one_source(self) -> "AnnotationSource":
        if (self.chat_id is None) == (self.paper_id is None):
            raise ValueError("an annotation needs exactly one chat or paper source")
        if (self.chat_id is None) != (self.chat_message_id is None):
            raise ValueError("chat annotations need both chat and message ids")
        if self.paper_id is None and self.paper_chunk_ordinal is not None:
            raise ValueError("only paper annotations can name a paper chunk")
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("annotation offsets must be supplied together")
        if self.start_offset is not None and self.end_offset <= self.start_offset:
            raise ValueError("annotation end offset must follow its start")
        return self


class AnnotationCreate(BaseModel):
    id: uuid.UUID
    phrase: str = Field(..., min_length=1, max_length=MAX_PHRASE_CHARS)
    surrounding_context: Optional[str] = Field(None, max_length=MAX_CONTEXT_CHARS)
    source: AnnotationSource


class UserAnnotationOut(AnnotationCreate):
    #: Null until the definition arrives, and after a failed attempt.
    definition: Optional[str]
    position: int
    created_at: dt.datetime
    updated_at: dt.datetime


class UserAnnotationList(BaseModel):
    annotations: list[UserAnnotationOut] = Field(default_factory=list)
