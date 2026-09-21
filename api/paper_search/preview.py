"""The short abstract shown on each chat result card."""

from __future__ import annotations

from typing import Optional

#: Characters of abstract kept before the ellipsis.
ABSTRACT_PREVIEW_CHARS = 300


def abstract_preview(
    abstract: Optional[str], limit: int = ABSTRACT_PREVIEW_CHARS
) -> Optional[str]:
    """The first `limit` characters of the abstract, with an ellipsis if cut.

    Whitespace is collapsed first: the abstract is joined from several chunks,
    and their line breaks would otherwise count toward the limit.
    """
    if not abstract:
        return None
    collapsed = " ".join(abstract.split())
    if len(collapsed) <= limit:
        return collapsed or None
    return collapsed[:limit].rstrip() + "…"
