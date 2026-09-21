"""Types for paper search: internal terms and hits, and the public response."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field

#: `entity` searches mentions of the entities OpenAI confirmed; `full_text`
#: searches chunk text for the query's noun phrases when it confirmed none.
SearchMethod = Literal["entity", "full_text"]


@dataclass(frozen=True)
class SearchTerm:
    """One thing the query asks about. Coverage counts terms, not entity ids."""

    phrase: str
    #: Empty for a full-text term. Several for a phrase that resolved to more
    #: than one entity, whose mentions then count toward the same term.
    entity_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class TermHit:
    """How often one term occurs in one paper: mentions, or matching chunks."""

    paper_id: int
    term_index: int
    hits: int


@dataclass
class PaperScore:
    """One candidate paper, scored against every term it matched."""

    paper_id: int
    #: term index -> hits in this paper.
    term_hits: dict[int, int] = field(default_factory=dict)
    #: Sum over matched terms of IDF x ln(1 + hits).
    score: float = 0.0

    @property
    def terms_matched(self) -> int:
        return len(self.term_hits)

    @property
    def mentions(self) -> int:
        return sum(self.term_hits.values())


class SearchTermSummary(BaseModel):
    """A term as the search saw it, so a result can be explained."""

    phrase: str
    entity_ids: list[int] = Field(default_factory=list)
    #: Papers that matched the term at all: its document frequency.
    papers_matched: int
    #: IDF weight. Zero for a dropped term.
    weight: float
    #: Full-text only: set when the term matched too much of the corpus to
    #: discriminate, and was left out of scoring.
    dropped: bool = False


class EvidenceChunk(BaseModel):
    """A passage showing why a paper was selected."""

    chunk_id: int
    section_type: Optional[str] = None
    text: str
    #: Query-entity mentions in the chunk, or its summed `ts_rank`.
    score: float


class SearchedPaper(BaseModel):
    paper_id: int
    pmid: int
    pmcid: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    pub_year: Optional[int] = None
    #: The primary sort key: how many distinct query terms the paper matched.
    terms_matched: int
    #: Total hits across those terms.
    mentions: int
    #: The IDF-weighted secondary sort key.
    score: float
    #: Why the paper earned a slot: broadest coverage, the most mentions of a
    #: particular term, or rank alone.
    selected_by: list[str] = Field(default_factory=list)
    chunks: list[EvidenceChunk] = Field(default_factory=list)


class PaperSearchResult(BaseModel):
    method: SearchMethod
    terms: list[SearchTermSummary] = Field(default_factory=list)
    #: Papers matching at least one scored term, before selection.
    papers_considered: int = 0
    papers: list[SearchedPaper] = Field(default_factory=list)
