"""`api.corpus.rag.wants_papers` — which routed tools run paper search."""

from __future__ import annotations

from typing import Optional

from api.corpus.models import RagSearchResponse
from api.corpus.rag import wants_papers
from api.llm.models import IntentResult


def _response(tool: Optional[str]) -> RagSearchResponse:
    intent = IntentResult(tool=tool, model="test") if tool else None
    return RagSearchResponse(query="q", intent=intent)


def testwants_papers() -> None:
    cases = [
        {"tool": "paper_search", "expected": True},
        {"tool": "paper_analysis", "expected": True},
        {"tool": "no_match", "expected": False},
        # Routing unconfigured or failed: noun-phrase search still answers.
        {"tool": None, "expected": True},
    ]
    for case in cases:
        assert wants_papers(_response(case["tool"])) is case["expected"], case
