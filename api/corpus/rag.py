"""The chat pipeline behind `/corpus/rag_search`, as a stream of NDJSON lines.

Each stage's output is sent the moment it exists:

1. `entity_matches` — the query's candidates, before OpenAI is asked anything.
2. `result` — the routed tool, the papers, and any citations.
3. `answer_delta`s, then `answer_done` — a `paper_analysis` answer as written.
4. `answer_entities` — the entities that answer names, found only once it is
   finished, so the answer is never held up for them.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from pydantic import BaseModel

from api.app.config import get_settings
from api.corpus.models import (
    AnswerDeltaEvent,
    AnswerDoneEvent,
    AnswerEntitiesEvent,
    EntityMatchesEvent,
    RagResultEvent,
    RagSearchResponse,
)
from api.db import session_scope
from api.entity_matching import (
    EntityMatchGroup,
    EntityMatchManager,
    QueryFragment,
    extract_query_fragments,
    filter_entity_matches,
    get_cutoffs,
)
from api.ingestion.embedding import embed_queries
from api.llm import LlmClient, LlmError, classify_intent, find_answer_entities, get_llm_client
from api.paper_analysis import (
    PaperAnalysisResult,
    gather_evidence,
    query_entity_ids,
    start_analysis,
    stream_answer,
)
from api.paper_search import search_papers

log = logging.getLogger(__name__)


def match_query_entities(text: str, fragments: list[QueryFragment]) -> RagSearchResponse:
    """Raw and filtered entity candidates for the query's fragments.

    Run before the response starts, so a failure here is still an HTTP error.
    """
    entity_matches = entity_candidates(fragments)
    return RagSearchResponse(
        query=text,
        entity_matches=entity_matches,
        filtered_entity_matches=filter_entity_matches(entity_matches, text, get_cutoffs()),
    )


def rag_events(result: RagSearchResponse, fragments: list[QueryFragment]) -> Iterator[str]:
    """Every stage's line, in order, each as soon as it is ready.

    Starlette iterates a sync generator in its threadpool, so the blocking
    database and OpenAI calls never stall the event loop.
    """
    yield ndjson_line(
        EntityMatchesEvent(
            entity_matches=result.entity_matches,
            filtered_entity_matches=result.filtered_entity_matches,
        )
    )
    _answer_query(result, fragments)
    yield ndjson_line(RagResultEvent(result=result))
    if result.analysis is not None:
        yield from _answer_events(result, result.analysis)


def entity_candidates(fragments: list[QueryFragment]) -> list[EntityMatchGroup]:
    """Every extraction/matcher/source path's candidates for `fragments`."""
    settings = get_settings()
    vectors = embed_queries([fragment.text for fragment in fragments])
    with session_scope() as session:
        return EntityMatchManager(
            session,
            top_k=settings.entity_match_top_k,
            embedding_threshold=settings.entity_match_embedding_threshold,
            trigram_threshold=settings.entity_match_trigram_threshold,
        ).search(fragments, vectors)


def ndjson_line(event: BaseModel) -> str:
    return event.model_dump_json() + "\n"


def wants_papers(result: RagSearchResponse) -> bool:
    """Every tool but `no_match` searches. So does chat when routing could not
    run: with no confirmed entities, the noun-phrase search still answers."""
    return result.intent is None or result.intent.tool != "no_match"


def wants_analysis(result: RagSearchResponse) -> bool:
    """Only an explicit `paper_analysis` route, and only with papers to read."""
    return (
        result.intent is not None
        and result.intent.tool == "paper_analysis"
        and result.search_method is not None
        and bool(result.papers)
    )


def _answer_query(result: RagSearchResponse, fragments: list[QueryFragment]) -> None:
    """Route, search and gather citations: everything the `result` line holds."""
    _route_intent(result)
    if wants_papers(result):
        _search_papers(result, fragments)
    if wants_analysis(result):
        _analyze_papers(result)
    log.info(
        "rag_search %r -> tool %s, %s search over %d terms, %d of %d papers",
        result.query,
        result.intent.tool if result.intent else None,
        result.search_method,
        len(result.search_terms),
        len(result.papers),
        result.papers_considered,
    )


def _answer_events(result: RagSearchResponse, analysis: PaperAnalysisResult) -> Iterator[str]:
    """The answer as it is written, then the entities it names."""
    client = get_llm_client()
    pieces = stream_answer(
        client,
        result.query,
        analysis,
        result.papers,
        timeout=get_settings().openai_analysis_timeout_seconds,
    )
    for piece in pieces:
        yield ndjson_line(AnswerDeltaEvent(text=piece))
    yield ndjson_line(
        AnswerDoneEvent(answer=analysis.answer, model=analysis.model, error=analysis.error)
    )
    if client is not None and analysis.answer is not None:
        yield ndjson_line(_answer_entities(client, analysis.answer))


def _answer_entities(client: LlmClient, answer: str) -> AnswerEntitiesEvent:
    """Run the query's matching over the answer, with a larger candidate
    cap, and let OpenAI confirm which candidates it really names."""
    groups = entity_candidates(extract_query_fragments(answer))
    filtered = filter_entity_matches(
        groups,
        answer,
        get_cutoffs(),
        max_per_strategy=get_settings().answer_entity_candidates_per_strategy,
    )
    try:
        return AnswerEntitiesEvent(entities=find_answer_entities(client, answer, filtered))
    except LlmError as exc:
        log.warning("answer entity matching failed: %s", exc)
        return AnswerEntitiesEvent(error=str(exc))


def _route_intent(result: RagSearchResponse) -> None:
    """Fill `result.intent`, or `intent_error` — never fail the search itself."""
    client = get_llm_client()
    if client is None:
        result.intent_error = "OpenAI is not configured (OPENAI_API_KEY is unset)"
        return
    try:
        result.intent = classify_intent(client, result.query, result.filtered_entity_matches)
    except LlmError as exc:
        log.warning("intent routing failed for %r: %s", result.query, exc)
        result.intent_error = str(exc)


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


def _analyze_papers(result: RagSearchResponse) -> None:
    """Fill `result.analysis` with its citations; `_answer_events` writes the
    answer. The paragraphs are read in a session closed before OpenAI is
    called, for the same reason as `_search_papers`."""
    settings = get_settings()
    assert result.search_method is not None  # guaranteed by wants_analysis
    with session_scope() as session:
        evidence = gather_evidence(
            session,
            result.search_method,
            result.search_terms,
            result.papers,
            dense_per_paper=settings.paper_analysis_dense_paragraphs,
            duplicate_similarity=settings.paper_analysis_duplicate_similarity,
        )
    result.analysis = start_analysis(
        get_llm_client(), evidence, query_entity_ids(result.search_terms)
    )
