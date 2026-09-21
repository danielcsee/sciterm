"""Re-score trigram candidates by edit distance.

Trigram similarity is good at *finding* a misspelled name but poor at scoring
it: one substituted letter removes up to three trigrams, so "osteoperosis"
scores only 0.625 against "Osteoporosis". Normalised Levenshtein charges that
same typo a single edit, 1 - 1/12 = 0.917.
"""

from __future__ import annotations

from collections.abc import Sequence

from api.entity_matching.models import EntityMatch


def rescore_by_edit_distance(
    fragment: str, matches: Sequence[EntityMatch]
) -> list[EntityMatch]:
    """Replace each score with edit similarity to `fragment`, best first."""
    rescored = [
        match.model_copy(
            update={"score": round(edit_similarity(fragment, match.matched_text), 6)}
        )
        for match in matches
    ]
    return sorted(rescored, key=lambda match: match.score, reverse=True)


def edit_similarity(left: str, right: str) -> float:
    """Case-insensitive `1 - levenshtein / longer length`, in [0, 1]."""
    left, right = left.casefold(), right.casefold()
    longest = max(len(left), len(right))
    if longest == 0:
        return 1.0
    return 1 - _levenshtein(left, right) / longest


def _levenshtein(left: str, right: str) -> int:
    """Insertions, deletions and substitutions, one row of the table at a time."""
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]
