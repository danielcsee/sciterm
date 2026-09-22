"""Request and response shapes for POST /define."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from api.annotations.schemas import AnnotationCreate, UserAnnotationOut

#: Generous for a highlight; it bounds what one click can spend on tokens.
MAX_PHRASE_CHARS = 2_000
#: A long paragraph. Anything past this is not "the paragraph it was in".
MAX_CONTEXT_CHARS = 8_000


class DefineTermRequest(BaseModel):
    phrase: str = Field(..., min_length=1, max_length=MAX_PHRASE_CHARS)
    #: The paragraph the phrase was highlighted in; null for long highlights.
    surrounding_context: Optional[str] = Field(None, max_length=MAX_CONTEXT_CHARS)
    annotation: Optional[AnnotationCreate] = None

    @field_validator("phrase")
    @classmethod
    def _phrase_has_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("phrase must contain text")
        return value

    @field_validator("surrounding_context")
    @classmethod
    def _blank_context_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _annotation_matches_request(self) -> "DefineTermRequest":
        if self.annotation is None:
            return self
        if self.annotation.phrase.strip() != self.phrase:
            raise ValueError("annotation phrase must match the requested phrase")
        if self.annotation.surrounding_context != self.surrounding_context:
            raise ValueError("annotation context must match the requested context")
        return self


class DefineTermResponse(BaseModel):
    definition: str
    annotation: Optional[UserAnnotationOut] = None
