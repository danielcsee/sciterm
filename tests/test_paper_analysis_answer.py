"""`api.paper_analysis.answer` — when an answer is asked for, and how it ends."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Optional

from api.llm import LlmError
from api.paper_analysis.answer import (
    EMPTY_ANSWER,
    NO_CLIENT,
    NO_EVIDENCE,
    start_analysis,
    stream_answer,
)
from api.paper_analysis.models import Citation, Evidence, PaperAnalysisResult


class FakeClient:
    """Stands in for `LlmClient`: yields `pieces`, then raises `error` if set."""

    model = "fake-model"

    def __init__(self, pieces: Sequence[str], error: Optional[LlmError] = None) -> None:
        self._pieces = pieces
        self._error = error
        self.calls = 0

    def stream_text(self, instructions: str, user_input: str, *, timeout: float) -> Iterator[str]:
        self.calls += 1
        yield from self._pieces
        if self._error is not None:
            raise self._error


def _citation(number: int) -> Citation:
    return Citation(
        number=number,
        paper_id=1,
        chunk_id=number,
        ordinal=number,
        text=f"paragraph {number}",
        selected_by="most mentions",
    )


def _evidence(count: int) -> Evidence:
    return Evidence(citations=[_citation(n) for n in range(1, count + 1)], rejected=2)


def _run(client: Optional[FakeClient], result: PaperAnalysisResult) -> list[str]:
    return list(stream_answer(client, "q?", result, [], timeout=1.0))  # type: ignore[arg-type]


def test_start_analysis() -> None:
    cases = [
        {"client": FakeClient([]), "count": 2, "error": None},
        {"client": FakeClient([]), "count": 0, "error": NO_EVIDENCE},
        {"client": None, "count": 2, "error": NO_CLIENT},
    ]
    for case in cases:
        result = start_analysis(case["client"], _evidence(case["count"]), [7, 8])  # type: ignore[arg-type]
        assert result.error == case["error"], case
        assert result.answer is None, case
        assert len(result.citations) == case["count"], case
        assert result.entity_ids == [7, 8], case
        assert result.duplicates_rejected == 2, case


def test_stream_answer_outcomes() -> None:
    cases = [
        {
            "pieces": ["BRCA1 ", "repairs [1].", "\n"],
            "error": None,
            "expected": {"answer": "BRCA1 repairs [1].", "model": "fake-model", "error": None},
        },
        {
            "pieces": [" ", "\n"],
            "error": None,
            "expected": {"answer": None, "model": None, "error": EMPTY_ANSWER},
        },
        # Text already sent stays sent; the result still records the failure.
        {
            "pieces": ["Partial"],
            "error": LlmError("timed out"),
            "expected": {"answer": None, "model": None, "error": "timed out"},
        },
    ]
    for case in cases:
        client = FakeClient(case["pieces"], case["error"])
        result = start_analysis(client, _evidence(1), [])  # type: ignore[arg-type]
        assert _run(client, result) == case["pieces"], case
        outcome = {"answer": result.answer, "model": result.model, "error": result.error}
        assert outcome == case["expected"], case


def test_stream_answer_skips_the_model_when_start_failed() -> None:
    client = FakeClient(["never"])
    result = start_analysis(client, _evidence(0), [])  # type: ignore[arg-type]
    assert _run(client, result) == []
    assert client.calls == 0
    assert result.error == NO_EVIDENCE
