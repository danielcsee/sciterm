"""Turn gathered evidence into a cited answer, streamed as it is written.

`start_analysis` packages the citations, which can be shown at once;
`stream_answer` then writes the answer. Neither raises: failures explain
themselves in `PaperAnalysisResult.error`, and the citations still return.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from typing import Optional

from api.llm import AnalysisPassage, LlmClient, LlmError, stream_analysis
from api.paper_analysis.models import Citation, Evidence, PaperAnalysisResult
from api.paper_search import SearchedPaper

log = logging.getLogger(__name__)

NO_EVIDENCE = "No paragraph in the matched papers mentions what you asked about."
NO_CLIENT = "OpenAI is not configured (OPENAI_API_KEY is unset)"
EMPTY_ANSWER = "OpenAI returned an empty answer"


def start_analysis(
    client: Optional[LlmClient], evidence: Evidence, entity_ids: Sequence[int]
) -> PaperAnalysisResult:
    """The citations, with `error` already set when no answer can be written."""
    result = PaperAnalysisResult(
        citations=evidence.citations,
        entity_ids=list(entity_ids),
        duplicates_rejected=evidence.rejected,
    )
    if not evidence.citations:
        result.error = NO_EVIDENCE
    elif client is None:
        result.error = NO_CLIENT
    return result


def stream_answer(
    client: Optional[LlmClient],
    question: str,
    result: PaperAnalysisResult,
    papers: Sequence[SearchedPaper],
    *,
    timeout: float,
) -> Iterator[str]:
    """Yield the answer as the model writes it, then fill in `result`.

    Yields nothing when `start_analysis` already found a reason not to ask.
    Once exhausted, `result.answer` and `result.model` are set, or `error` is.
    """
    if client is None or result.error is not None:
        return
    passages = analysis_passages(result.citations, papers)
    pieces: list[str] = []
    try:
        for piece in stream_analysis(client, question, passages, timeout=timeout):
            pieces.append(piece)
            yield piece
    except LlmError as exc:
        log.warning("paper analysis failed for %r: %s", question, exc)
        result.error = str(exc)
        return
    _finish(result, "".join(pieces).strip(), client.model)


def analysis_passages(
    citations: Sequence[Citation], papers: Sequence[SearchedPaper]
) -> list[AnalysisPassage]:
    by_id = {paper.paper_id: paper for paper in papers}
    return [_passage(citation, by_id.get(citation.paper_id)) for citation in citations]


def _finish(result: PaperAnalysisResult, answer: str, model: str) -> None:
    if not answer:
        result.error = EMPTY_ANSWER
        return
    result.answer = answer
    result.model = model


def _passage(citation: Citation, paper: Optional[SearchedPaper]) -> AnalysisPassage:
    return AnalysisPassage(
        number=citation.number,
        paper=paper.title if paper else None,
        year=paper.pub_year if paper else None,
        section=citation.section_type,
        text=citation.text,
    )
