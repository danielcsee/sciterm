"""Answer a question from numbered paragraphs, citing them as [n]."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from typing import Optional

from api.llm.client import LlmClient

ANALYSIS_INSTRUCTIONS = """\
You answer questions about scientific literature for a researcher. The input \
is JSON holding the user's `question` and numbered `passages`, each quoted \
from a paper with its title, year and section.

- Answer the question using only the passages. Do not add outside knowledge.
- Synthesize across papers: say where they agree, where they differ, and what \
the evidence does not settle.
- Cite every claim with the numbers of the passages supporting it, written as \
[1] or [1][3]. Never cite a number that was not given.
- If the passages do not answer the question, say so plainly.
- Be concise: at most 250 words of plain prose in short paragraphs, no \
headings or lists."""


@dataclass(frozen=True)
class AnalysisPassage:
    """One paragraph as the model sees it."""

    number: int
    paper: Optional[str]
    year: Optional[int]
    section: Optional[str]
    text: str


def stream_analysis(
    client: LlmClient,
    question: str,
    passages: Sequence[AnalysisPassage],
    *,
    timeout: float,
) -> Iterator[str]:
    """The model's cited answer, piece by piece. Raises LlmError on failure."""
    return client.stream_text(
        ANALYSIS_INSTRUCTIONS, analysis_input(question, passages), timeout=timeout
    )


def analysis_input(question: str, passages: Sequence[AnalysisPassage]) -> str:
    return json.dumps(
        {"question": question, "passages": [asdict(passage) for passage in passages]},
        ensure_ascii=False,
    )
