"""Pure near-duplicate rejection over precomputed paragraph similarities.

Measured on this corpus (bge-base-en-v1.5): exact copies score 1.000, but
paragraphs reporting *different* numbers in the same template ("Data from
1995: ..." vs "Data from 2010-2015: ...") score 0.96-0.98. Only a threshold
above that band rejects copies without rejecting distinct findings.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

#: Unordered chunk-id pair -> cosine similarity.
Similarities = Mapping[frozenset[int], float]


def drop_near_duplicates(
    chunk_ids: Sequence[int], similarities: Similarities, threshold: float
) -> tuple[list[int], list[int]]:
    """Keep chunks in priority order, dropping any too similar to one kept.

    A pair missing from `similarities` (no embedding) is never a duplicate.
    Returns (kept, rejected), each in the order given.
    """
    kept: list[int] = []
    rejected: list[int] = []
    for chunk_id in chunk_ids:
        if chunk_id in kept or _duplicates_any(chunk_id, kept, similarities, threshold):
            rejected.append(chunk_id)
        else:
            kept.append(chunk_id)
    return kept, rejected


def _duplicates_any(
    chunk_id: int, kept: Sequence[int], similarities: Similarities, threshold: float
) -> bool:
    return any(
        similarities.get(frozenset((chunk_id, other)), 0.0) >= threshold for other in kept
    )
