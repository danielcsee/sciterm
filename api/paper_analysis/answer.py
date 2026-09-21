"""Turn gathered evidence into a cited answer. Never raises: failures explain
themselves in `PaperAnalysisResult.error`, and the citations still return."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Optional

from api.llm import AnalysisPassage, LlmClient, LlmError, write_analysis
from api.paper_analysis.models import Citation, Evidence, PaperAnalysisResult
from api.paper_search import SearchedPaper

log = logging.getLogger(__name__)

NO_EVIDENCE = "No paragraph in the matched papers mentions what you asked about."
NO_CLIENT = "OpenAI is not configured (OPENAI_API_KEY is unset)"


def answer_question(
    client: Optional[LlmClient],
    question: str,
    evidence: Evidence,
    papers: Sequence[SearchedPaper],
    entity_ids: Sequence[int],
    *,
    timeout: float,
) -> PaperAnalysisResult:
    """Ask the model to answer from the evidence, and package the result."""
    result = PaperAnalysisResult(
        citations=evidence.citations,
        entity_ids=list(entity_ids),
        duplicates_rejected=evidence.rejected,
    )
    if not evidence.citations:
        result.error = NO_EVIDENCE
    elif client is None:
        result.error = NO_CLIENT
    else:
        _generate(result, client, question, analysis_passages(evidence.citations, papers), timeout)
    return result


def analysis_passages(
    citations: Sequence[Citation], papers: Sequence[SearchedPaper]
) -> list[AnalysisPassage]:
    by_id = {paper.paper_id: paper for paper in papers}
    return [_passage(citation, by_id.get(citation.paper_id)) for citation in citations]


def _generate(
    result: PaperAnalysisResult,
    client: LlmClient,
    question: str,
    passages: list[AnalysisPassage],
    timeout: float,
) -> None:
    try:
        result.answer = write_analysis(client, question, passages, timeout=timeout)
        result.model = client.model
    except LlmError as exc:
        log.warning("paper analysis failed for %r: %s", question, exc)
        result.error = str(exc)


def _passage(citation: Citation, paper: Optional[SearchedPaper]) -> AnalysisPassage:
    return AnalysisPassage(
        number=citation.number,
        paper=paper.title if paper else None,
        year=paper.pub_year if paper else None,
        section=citation.section_type,
        text=citation.text,
    )
