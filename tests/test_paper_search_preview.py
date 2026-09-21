"""`api.paper_search.preview` — the abstract cut for a chat result card."""

from __future__ import annotations

from api.paper_search.preview import ABSTRACT_PREVIEW_CHARS, abstract_preview


def test_short_abstract_is_kept_whole() -> None:
    assert abstract_preview("A short abstract.") == "A short abstract."


def test_exactly_the_limit_gets_no_ellipsis() -> None:
    text = "x" * ABSTRACT_PREVIEW_CHARS
    assert abstract_preview(text) == text


def test_long_abstract_is_cut_at_the_limit_with_an_ellipsis() -> None:
    preview = abstract_preview("y" * (ABSTRACT_PREVIEW_CHARS + 50))
    assert preview == "y" * ABSTRACT_PREVIEW_CHARS + "…"


def test_whitespace_is_collapsed_before_counting() -> None:
    assert abstract_preview("one\n\n  two\tthree") == "one two three"
    assert abstract_preview("a" + " " * 400 + "b") == "a b"


def test_trailing_space_before_the_ellipsis_is_dropped() -> None:
    assert abstract_preview("abcd efgh", limit=5) == "abcd…"


def test_missing_abstract_has_no_preview() -> None:
    assert abstract_preview(None) is None
    assert abstract_preview("") is None
    assert abstract_preview("   ") is None
