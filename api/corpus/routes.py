"""HTTP surface for the stored corpus, mounted at /corpus.

Sync (`def`, not `async def`) for the same reason as the ingestion routes: the
queries block on SQLAlchemy, so FastAPI runs them in its threadpool rather than
stalling the event loop.
"""

from __future__ import annotations

import logging
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from api.auth import require_user
from api.corpus import queries
from api.ncbi.errors import NcbiError
from api.corpus.models import (
    EntitySpan,
    PaperEntityItem,
    PaperEntityList,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    CorpusPage,
    CorpusPaperDetail,
    ImportedReferenceList,
    RagSearchResponse,
    ReferenceList,
)
from api.app.config import get_settings
from api.entity_matching import (
    EntityMatchManager,
    QueryFragment,
    extract_query_fragments,
    filter_entity_matches,
    get_cutoffs,
)
from api.ingestion.embedding import embed_queries
from api.llm import LlmError, classify_intent, get_llm_client
from api.paper_search import search_papers
from api.pb_client import PubTatorClient
from api.db import session_scope

log = logging.getLogger(__name__)

#: Reading the stored corpus. Free: these queries never leave the machine and
#: cost nothing, so an anonymous visitor gets the whole app populated with real
#: papers rather than an empty shell behind a login wall.
router = APIRouter(tags=["corpus"])

#: The metered half of the corpus surface, gated as a router rather than route
#: by route so anything added here is protected the day it is written.
#: `rag_search` is the chat window (and where an LLM will land); `references`
#: fetches full papers from PubTator and spends the NCBI budget.
protected_router = APIRouter(tags=["corpus"], dependencies=[Depends(require_user)])


@router.get("/corpus", response_model=CorpusPage, summary="List imported papers")
def list_corpus(
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Papers per page."
    ),
) -> CorpusPage:
    """Papers that finished importing, most recent first.

    Only papers whose final stage is `done` appear. A paper that is queued,
    mid-import or failed has rows in `papers` already, but it is not in the
    corpus until it has content — so this joins the stage ledger rather than
    reading `papers` directly.

    A page beyond the end returns an empty list rather than a 404: the reader
    is scrolling, and running off the end is normal, not an error.
    """
    with session_scope() as session:
        total = queries.count_papers(session)
        papers = queries.list_papers(
            session, limit=page_size, offset=(page - 1) * page_size
        )

    return CorpusPage(
        page=page,
        page_size=page_size,
        total_papers=total,
        total_pages=ceil(total / page_size) if total else 0,
        papers=papers,
    )


@protected_router.get(
    "/corpus/rag_search",
    response_model=RagSearchResponse,
    summary="Route a chat query and search imported papers",
)
def rag_search(
    query: str = Query(..., min_length=2, description="Free-text question."),
) -> RagSearchResponse:
    """Entity matching, OpenAI intent routing, then paper search. No generated answer yet.

    Candidate entities are matched from the query's fragments and filtered;
    OpenAI picks the tool the query calls for and confirms which candidates it
    names. `paper_search` and `paper_analysis` both run `api.paper_search`,
    which searches by the confirmed entities, or by the query's noun phrases
    when there are none. `no_match` returns no papers.

    Registered before `/corpus/{paper_id}`: FastAPI matches routes in order,
    and "rag_search" against an int path parameter is a 422.
    """
    text = query.strip()
    if not text:
        raise HTTPException(status_code=400, detail="query must not be blank")

    fragments = extract_query_fragments(text)
    result = _match_entities(text, fragments)
    _route_intent(result, text)
    if _wants_papers(result):
        _search_papers(result, fragments)
    log.info(
        "rag_search %r -> tool %s, %s search over %d terms, %d of %d papers",
        text,
        result.intent.tool if result.intent else None,
        result.search_method,
        len(result.search_terms),
        len(result.papers),
        result.papers_considered,
    )
    return result


def _match_entities(text: str, fragments: list[QueryFragment]) -> RagSearchResponse:
    """Raw and filtered entity candidates for the query's fragments."""
    settings = get_settings()
    vectors = embed_queries([fragment.text for fragment in fragments])
    with session_scope() as session:
        entity_matches = EntityMatchManager(
            session,
            top_k=settings.entity_match_top_k,
            embedding_threshold=settings.entity_match_embedding_threshold,
            trigram_threshold=settings.entity_match_trigram_threshold,
        ).search(fragments, vectors)
    return RagSearchResponse(
        query=text,
        entity_matches=entity_matches,
        filtered_entity_matches=filter_entity_matches(entity_matches, text, get_cutoffs()),
    )


def _route_intent(result: RagSearchResponse, text: str) -> None:
    """Fill `result.intent`, or `intent_error` — never fail the search itself."""
    client = get_llm_client()
    if client is None:
        result.intent_error = "OpenAI is not configured (OPENAI_API_KEY is unset)"
        return
    try:
        result.intent = classify_intent(client, text, result.filtered_entity_matches)
    except LlmError as exc:
        log.warning("intent routing failed for %r: %s", text, exc)
        result.intent_error = str(exc)


def _wants_papers(result: RagSearchResponse) -> bool:
    """Every tool but `no_match` searches. So does chat when routing could not
    run: with no confirmed entities, the noun-phrase search still answers."""
    return result.intent is None or result.intent.tool != "no_match"


def _search_papers(result: RagSearchResponse, fragments: list[QueryFragment]) -> None:
    """Fill the paper fields of `result`. Its own session: routing may have
    held the request for seconds, and no connection should wait on OpenAI."""
    settings = get_settings()
    entities = result.intent.entities if result.intent else []
    with session_scope() as session:
        found = search_papers(
            session,
            entities,
            fragments,
            top_k=settings.paper_search_top_k,
            chunks_per_paper=settings.paper_search_chunks_per_paper,
            max_term_fraction=settings.paper_search_max_term_fraction,
        )
    result.papers = found.papers
    result.search_method = found.method
    result.search_terms = found.terms
    result.papers_considered = found.papers_considered


@protected_router.get(
    "/corpus/{paper_id}/references",
    response_model=ReferenceList,
    summary="Importable references of a stored paper",
)
async def paper_references(
    request: Request, paper_id: int = Path(..., ge=1)
) -> ReferenceList:
    """The references of a stored paper that exist as full Papers in PubTator.

    Every entry returned is importable, so a count taken from the list is exact
    rather than an optimistic upper bound.

    This is the heavy call, and it has to be: the light export reports
    `pmcid: null` even for papers that *are* in PMC, so nothing cheaper can
    answer "does a full Paper exist". References without a PMID are skipped
    outright — the export is PMID-keyed and cannot be asked about them.

    Async, unlike its neighbours: the PubTator round-trip dominates, and
    holding a threadpool worker for several seconds of network wait would be
    the wrong resource to block.
    """
    with session_scope() as session:
        paper = queries.get_paper(session, paper_id)
        if paper is None:
            raise HTTPException(
                status_code=404, detail=f"paper {paper_id} is not in your corpus"
            )
        pmids, total, with_pmid = queries.reference_pmids(session, paper_id)

    truncated = len(pmids) > queries.MAX_REFERENCE_LOOKUP
    pmids = pmids[: queries.MAX_REFERENCE_LOOKUP]

    references: list = []
    if pmids:
        pubtator: PubTatorClient = request.app.state.pubtator
        try:
            fetched = await pubtator.fetch_papers(pmids, full=True)
        except NcbiError as exc:
            log.warning("references for paper %s failed: %s", paper_id, exc.message)
            raise HTTPException(status_code=exc.status, detail=exc.message) from exc
        references = [
            queries.to_search_result(item) for item in fetched if item.importable
        ]

    log.info(
        "paper %s references: %d total, %d with pmid, %d importable",
        paper_id,
        total,
        with_pmid,
        len(references),
    )
    return ReferenceList(
        paper_id=paper_id,
        pmid=paper.pmid,
        total_references=total,
        with_pmid=with_pmid,
        truncated=truncated,
        references=references,
    )


@router.get(
    "/corpus/{paper_id}/imported-references",
    response_model=ImportedReferenceList,
    summary="Imported papers that reference a stored paper",
)
def paper_imported_references(
    paper_id: int = Path(..., ge=1),
) -> ImportedReferenceList:
    """Papers already in the corpus whose bibliographies cite this paper."""
    with session_scope() as session:
        pmid = queries.imported_paper_pmid(session, paper_id)
        if pmid is None:
            raise HTTPException(
                status_code=404, detail=f"paper {paper_id} is not in your corpus"
            )
        papers = queries.imported_references(session, pmid)

    return ImportedReferenceList(
        paper_id=paper_id,
        total=len(papers),
        papers=papers,
    )


@router.get(
    "/corpus/{paper_id}/entities",
    response_model=PaperEntityList,
    summary="Grounded concepts mentioned in a stored paper",
)
def paper_entities(paper_id: int = Path(..., ge=1)) -> PaperEntityList:
    """Every entity this paper mentions, most-mentioned first.

    Sync, unlike its `/references` neighbour: this is one grouped Postgres
    query and never leaves the machine, so it belongs in the threadpool rather
    than on the event loop.
    """
    with session_scope() as session:
        if queries.get_paper(session, paper_id) is None:
            raise HTTPException(
                status_code=404, detail=f"paper {paper_id} is not in your corpus"
            )
        rows = queries.paper_entities(session, paper_id)

    return PaperEntityList(
        paper_id=paper_id,
        total=len(rows),
        entities=[PaperEntityItem(**row) for row in rows],
    )


@router.get(
    "/corpus/{paper_id}",
    response_model=CorpusPaperDetail,
    summary="Read one imported paper",
)
def read_paper(paper_id: int = Path(..., ge=1)) -> CorpusPaperDetail:
    """The whole paper: metadata, authors, paragraphs in order, references.

    404 for a paper that does not exist *or* has not finished importing — the
    reader must not be handed a half-ingested document.
    """
    with session_scope() as session:
        paper = queries.get_paper(session, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"paper {paper_id} is not in your corpus")
    return paper
