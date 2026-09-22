"""`api.paper_analysis.dedupe` — greedy near-duplicate rejection."""

from __future__ import annotations

from api.paper_analysis.dedupe import drop_near_duplicates


def _pair(a: int, b: int) -> frozenset[int]:
    return frozenset((a, b))


def test_drop_near_duplicates() -> None:
    cases = [
        {"ids": [], "similarities": {}, "threshold": 0.9, "expected": ([], [])},
        {
            # Missing pairs (no embedding) are never duplicates.
            "ids": [1, 2, 3],
            "similarities": {},
            "threshold": 0.9,
            "expected": ([1, 2, 3], []),
        },
        {
            # At the threshold is a duplicate; just below it is not. The
            # earlier chunk wins, whichever order the pair key was built in.
            "ids": [1, 2, 3],
            "similarities": {_pair(2, 1): 0.9, _pair(1, 3): 0.899},
            "threshold": 0.9,
            "expected": ([1, 3], [2]),
        },
        {
            # Only kept chunks count: 3 duplicates the rejected 2, not 1.
            "ids": [1, 2, 3],
            "similarities": {_pair(1, 2): 0.99, _pair(2, 3): 0.99, _pair(1, 3): 0.5},
            "threshold": 0.95,
            "expected": ([1, 3], [2]),
        },
        {
            # A repeated id is rejected as a copy of itself.
            "ids": [4, 4],
            "similarities": {},
            "threshold": 0.95,
            "expected": ([4], [4]),
        },
    ]
    for case in cases:
        actual = drop_near_duplicates(case["ids"], case["similarities"], case["threshold"])
        assert actual == case["expected"]
