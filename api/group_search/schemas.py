"""Response shapes for group paper search."""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.corpus.models import CorpusPaper
from api.group_search.subgroups import SortOrder

#: Subgroups per page. A page holds whole subgroups, so its paper count varies.
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


class GroupPaper(CorpusPaper):
    """A corpus preview card plus how many of the group's entities it mentions."""

    match_count: int


class PaperSubgroup(BaseModel):
    """Papers whose paragraphs discuss similar topics, most matches first."""

    size: int
    papers: list[GroupPaper] = Field(default_factory=list)


class GroupPaperPage(BaseModel):
    group_id: int
    group_name: str
    order: SortOrder
    page: int
    page_size: int
    total_subgroups: int
    total_papers: int
    total_pages: int
    subgroups: list[PaperSubgroup] = Field(default_factory=list)
