"""Validated API shapes for saved chats."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from api.paper_search import SearchedPaper

MAX_CHAT_TITLE_LENGTH = 200
MAX_CHAT_MESSAGES = 200


class SavedCitation(BaseModel):
    number: int = Field(..., ge=1)
    paper_id: Optional[int] = Field(None, ge=1)
    chunk_id: Optional[int] = Field(None, ge=1)
    ordinal: int = Field(..., ge=0)
    section_type: Optional[str] = None
    text: str
    selected_by: str
    paper_pmid: Optional[int] = Field(None, ge=1)
    paper_title: Optional[str] = None


class SavedEntityPill(BaseModel):
    entity_id: Optional[int] = Field(None, ge=1)
    identifier: str
    entity_type: str
    name: Optional[str] = None
    phrases: list[str] = Field(default_factory=list)


class SavedChatMessage(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    status: Literal["done", "error"] = "done"
    fallback_text: Optional[str] = None
    response_kind: Optional[Literal["paper_search", "paper_analysis", "no_match"]] = None
    result_papers: list[SearchedPaper] = Field(default_factory=list)
    papers_considered: int = Field(0, ge=0)
    analysis_entity_ids: list[int] = Field(default_factory=list)
    analysis_duplicates_rejected: int = Field(0, ge=0)
    analysis_model: Optional[str] = None
    analysis_error: Optional[str] = None
    citations: list[SavedCitation] = Field(default_factory=list)
    entity_pills: list[SavedEntityPill] = Field(default_factory=list)

    @model_validator(mode="after")
    def _role_fields(self) -> "SavedChatMessage":
        if self.role == "user" and (
            self.response_kind is not None
            or self.result_papers
            or self.citations
            or self.entity_pills
        ):
            raise ValueError("user messages cannot carry assistant response data")
        if self.role == "assistant" and self.response_kind != "paper_analysis" and self.citations:
            raise ValueError("only paper_analysis messages can carry citations")
        return self


class SaveChatRequest(BaseModel):
    title: str = Field(..., max_length=MAX_CHAT_TITLE_LENGTH)
    messages: list[SavedChatMessage] = Field(
        ..., min_length=1, max_length=MAX_CHAT_MESSAGES
    )

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("a saved chat needs a title")
        return title

    @model_validator(mode="after")
    def _message_order(self) -> "SaveChatRequest":
        if self.messages[0].role != "user":
            raise ValueError("a saved chat must begin with a user query")
        if len({message.id for message in self.messages}) != len(self.messages):
            raise ValueError("message ids must be unique within a chat")
        return self


class SavedChatOut(SaveChatRequest):
    chat_id: int
    created_at: dt.datetime
    updated_at: dt.datetime


class SavedChatSummary(BaseModel):
    chat_id: int
    title: str
    message_count: int
    preview: str
    created_at: dt.datetime
    updated_at: dt.datetime


class SavedChatList(BaseModel):
    chats: list[SavedChatSummary] = Field(default_factory=list)
