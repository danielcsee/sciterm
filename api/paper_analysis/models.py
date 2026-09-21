"""Types for paper analysis: internal paragraph scores and the public response."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ParagraphHit:
    """How strongly one term occurs in one paragraph.

    `hits` is a mention count on the entity path and a `ts_rank` on the
    full-text path. Both only ever compare paragraphs within one search.
    """

    paper_id: int
    chunk_id: int
    term_index: int
    hits: float


@dataclass
class ParagraphScore:
    """One candidate paragraph, scored against every term it matched."""

    paper_id: int
    chunk_id: int
    #: term index -> hits in this paragraph.
    term_hits: dict[int, float] = field(default_factory=dict)

    @property
    def terms_matched(self) -> int:
        return len(self.term_hits)

    @property
    def density(self) -> float:
        """Hits summed over every query term: what the top picks rank by."""
        return sum(self.term_hits.values())


@dataclass(frozen=True)
class PickedParagraph:
    paper_id: int
    chunk_id: int
    #: `DENSITY_REASON` or `BREADTH_REASON`.
    reason: str


@dataclass(frozen=True)
class Evidence:
    """The paragraphs that survived selection and de-duplication."""

    citations: list[Citation]
    #: Candidates dropped as near-copies of a paragraph already kept.
    rejected: int


class Citation(BaseModel):
    """One numbered paragraph the answer may cite as `[number]`."""

    number: int
    paper_id: int
    chunk_id: int
    #: `PaperParagraph.ordinal`, so the reader can scroll to it.
    ordinal: int
    section_type: Optional[str] = None
    text: str
    #: Why the paragraph was picked: most mentions, or broadest coverage.
    selected_by: str


class PaperAnalysisResult(BaseModel):
    """The generated answer and the paragraphs it was grounded in."""

    #: Prose citing paragraphs as `[n]`. Null when generation failed or had
    #: nothing to work from; `error` then says why.
    answer: Optional[str] = None
    #: Grouped by paper, in paper rank order, and in reading order within one.
    citations: list[Citation] = Field(default_factory=list)
    #: The query's entities, for highlighting in the opened paper. Empty on
    #: the full-text path, which searched phrases rather than entities.
    entity_ids: list[int] = Field(default_factory=list)
    #: Paragraphs dropped as near-duplicates before prompting.
    duplicates_rejected: int = 0
    model: Optional[str] = None
    error: Optional[str] = None
