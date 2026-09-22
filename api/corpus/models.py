"""Response models for the corpus routes."""

from __future__ import annotations

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field

from api.pb_client.models import SearchResult
from api.entity_matching.models import EntityMatchGroup, EntityStrategyGroup
from api.llm.models import AnswerEntity, IntentResult
from api.paper_analysis import PaperAnalysisResult
from api.paper_search import SearchedPaper, SearchMethod, SearchTermSummary

#: Matches the frontend's infinite-scroll page size. Capped so one request
#: cannot ask for the whole corpus.
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class CorpusPaper(BaseModel):
    """A stored paper, shaped for the same preview card as a search result."""

    paper_id: int
    pmid: int
    pmcid: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    pub_year: Optional[int] = None
    doi: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    #: First abstract chunk where there is one, else the first chunk. Gives the
    #: card the same shape as a search result's snippet.
    snippet: Optional[str] = None
    chunk_count: int = 0
    has_full_text: bool = False
    #: When the final stage completed — the ordering key.
    imported_at: Optional[dt.datetime] = None


class CorpusPage(BaseModel):
    page: int
    page_size: int
    total_papers: int
    total_pages: int
    papers: list[CorpusPaper]


class PaperParagraph(BaseModel):
    """One stored chunk, as a unit of the rendered document."""

    ordinal: int
    section_type: Optional[str] = None
    #: PubTator's passage kind. `is_heading` derives from it; it is kept so the
    #: reader can distinguish a figure caption or table caption from prose.
    chunk_type: Optional[str] = None
    text: str

    @property
    def is_heading(self) -> bool:
        return bool(self.chunk_type and "title" in self.chunk_type)


class PaperReferenceOut(BaseModel):
    ordinal: int
    title: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    source: Optional[str] = None
    year: Optional[str] = None
    volume: Optional[str] = None
    fpage: Optional[str] = None
    lpage: Optional[str] = None


class CorpusPaperDetail(BaseModel):
    """A whole stored paper, enough to render it as a document."""

    paper_id: int
    pmid: int
    pmcid: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    journal_title: Optional[str] = None
    pub_year: Optional[int] = None
    volume: Optional[str] = None
    fpage: Optional[str] = None
    lpage: Optional[str] = None
    doi: Optional[str] = None
    has_full_text: bool = False
    imported_at: Optional[dt.datetime] = None
    authors: list[str] = Field(default_factory=list)
    #: In document order. The article title is excluded — it is `title`.
    paragraphs: list[PaperParagraph] = Field(default_factory=list)
    references: list[PaperReferenceOut] = Field(default_factory=list)
    #: Imported papers whose bibliographies point at this paper.
    imported_reference_count: int = 0


class ImportedReferenceList(BaseModel):
    """Imported papers whose bibliographies point at one stored paper."""

    paper_id: int
    total: int
    papers: list[CorpusPaper] = Field(default_factory=list)


# --------------------------------------------------------------------------
# RAG search
# --------------------------------------------------------------------------


class RagSearchResponse(BaseModel):
    query: str
    #: Chosen by `api.paper_search` when the query routes to `paper_search` or
    #: `paper_analysis`, or when routing could not run. Empty for `no_match`.
    papers: list[SearchedPaper] = Field(default_factory=list)
    #: Which search produced `papers`; null when none ran.
    search_method: Optional[SearchMethod] = None
    #: The terms that search scored, with their weights and match counts.
    search_terms: list[SearchTermSummary] = Field(default_factory=list)
    #: Papers matching at least one term, before the top few were selected.
    papers_considered: int = 0
    entity_matches: list[EntityMatchGroup] = Field(default_factory=list)
    filtered_entity_matches: list[EntityStrategyGroup] = Field(default_factory=list)
    #: The tool OpenAI routed the query to. Null when routing is unconfigured
    #: or failed; `intent_error` then says which, and search still answers.
    intent: Optional[IntentResult] = None
    intent_error: Optional[str] = None
    #: `paper_analysis` only: the cited answer and its paragraphs.
    analysis: Optional[PaperAnalysisResult] = None


#: `rag_search` streams newline-delimited JSON, one of these per line.
RAG_STREAM_MEDIA_TYPE = "application/x-ndjson"


class EntityMatchesEvent(BaseModel):
    """Always first, before OpenAI is asked anything: the query's candidates."""

    type: Literal["entity_matches"] = "entity_matches"
    entity_matches: list[EntityMatchGroup] = Field(default_factory=list)
    filtered_entity_matches: list[EntityStrategyGroup] = Field(default_factory=list)


class RagResultEvent(BaseModel):
    """Second: everything but the answer, citations included.

    For `paper_analysis`, `analysis.answer` is null here; the answer follows
    as `answer_delta` lines and closes with one `answer_done`.
    """

    type: Literal["result"] = "result"
    result: RagSearchResponse


class AnswerDeltaEvent(BaseModel):
    """The next piece of the answer, to append to what came before."""

    type: Literal["answer_delta"] = "answer_delta"
    text: str


class AnswerDoneEvent(BaseModel):
    """Only after a `paper_analysis` result: how the answer ended.

    `answer` is the whole text, trimmed; it replaces the concatenated deltas.
    """

    type: Literal["answer_done"] = "answer_done"
    answer: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None


class AnswerEntitiesEvent(BaseModel):
    """Last, and only after an answer was written: the entities it names.

    Each entity carries every phrase naming it, as written in `answer`.
    """

    type: Literal["answer_entities"] = "answer_entities"
    entities: list[AnswerEntity] = Field(default_factory=list)
    error: Optional[str] = None


class ReferenceList(BaseModel):
    """The importable references of a stored paper.

    Every entry is guaranteed to exist as a full Paper in PubTator, so a count
    taken from `references` is exact rather than optimistic.
    """

    paper_id: int
    pmid: int
    #: References recorded for the paper, importable or not.
    total_references: int
    #: Those carrying a PMID, i.e. the ones we could even ask PubTator about.
    with_pmid: int
    #: True when the reference list was longer than we were willing to query.
    truncated: bool = False
    #: Importable references, shaped as search results so the UI renders them
    #: with the same card. `score` and `text_hl` are search-only and stay null.
    references: list[SearchResult] = Field(default_factory=list)


class EntitySpan(BaseModel):
    """Where one mention sits in the rendered document.

    `start` is relative to the paragraph, not the document: the client slices
    `paragraph.text` directly and never learns the document coordinate space.

    `text` is what should be at that slice. Carrying it lets the client verify
    before highlighting — Postgres counts characters where JavaScript counts
    UTF-16 units, so a non-BMP character anywhere earlier in the paragraph
    would shift every later span. This corpus is pure ASCII today, which is a
    property of the data rather than a guarantee.
    """

    #: `PaperParagraph.ordinal`, so the client needs no chunk ids.
    ordinal: int
    start: int
    length: int
    text: str


class PaperEntityItem(BaseModel):
    """One grounded concept found in a paper, with how it was written there."""

    entity_id: int
    identifier: str
    entity_type: str
    database: str
    #: PubTator's canonical name. For Species it is the taxon number, which is
    #: why `names` matters: "9685" is not what anyone calls a cat.
    name: Optional[str] = None
    #: Distinct surface forms this paper used, most frequent first.
    names: list[str] = Field(default_factory=list)
    mention_count: int
    #: Every occurrence, in reading order.
    spans: list[EntitySpan] = Field(default_factory=list)


class PaperEntityList(BaseModel):
    paper_id: int
    total: int
    entities: list[PaperEntityItem] = Field(default_factory=list)
