"""`api.entity_matching.cutoffs` — per-matcher cutoffs loaded from TOML."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from api.entity_matching.cutoffs import MatchCutoffs, load_cutoffs

SHIPPED = Path(__file__).resolve().parents[1] / "api" / "entity_matching" / "cutoffs.toml"


def test_load_cutoffs(tmp_path: Path) -> None:
    cases = [
        {
            "name": "the shipped file is valid",
            "path": SHIPPED,
            "expected": MatchCutoffs(trigram=0.8, embedding=0.65),
        },
        {
            "name": "each method is read",
            "body": "trigram = 0.7\nembedding = 0.6\n",
            "expected": MatchCutoffs(trigram=0.7, embedding=0.6),
        },
        {"name": "missing method", "body": "trigram = 0.8\n", "raises": ValidationError},
        {
            "name": "out of range",
            "body": "trigram = 0.8\nembedding = 1.5\n",
            "raises": ValidationError,
        },
        {
            "name": "unknown key",
            "body": "trigram = 0.8\nembedding = 0.6\ntrigam = 0.7\n",
            "raises": ValidationError,
        },
    ]

    for index, case in enumerate(cases):
        path = case.get("path")
        if path is None:
            path = tmp_path / f"cutoffs_{index}.toml"
            path.write_text(case["body"])
        if "raises" in case:
            with pytest.raises(case["raises"]):
                load_cutoffs(path)
            continue
        assert load_cutoffs(path) == case["expected"], case["name"]


def test_for_method() -> None:
    cutoffs = MatchCutoffs(trigram=0.8, embedding=0.65)
    cases = [
        {"method": "trigram", "expected": 0.8},
        {"method": "embedding", "expected": 0.65},
    ]

    for case in cases:
        assert cutoffs.for_method(case["method"]) == case["expected"], case["method"]
