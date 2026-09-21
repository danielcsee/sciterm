"""Database access for group paper search: one manager over one session."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.corpus.queries import imported_papers_by_ids
from api.db.models import PaperStageRun
from api.group_search.queries import CORPUS_MEAN_SQL, GROUP_NAME_SQL, GROUP_PAPERS_SQL
from api.group_search.schemas import GroupPaper, GroupPaperPage, PaperSubgroup
from api.group_search.subgroups import (
    MatchedPaper,
    SortOrder,
    build_subgroups,
    order_subgroups,
    page_of,
)


class GroupSearchManager:
    """Find a group's papers and sort them into subgroups of similar topics.

    Nothing is stored: subgroups are recomputed on every call, so a newly
    ingested paper joins them on the next request.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self, group_id: int, order: SortOrder, page: int, page_size: int
    ) -> Optional[GroupPaperPage]:
        """One page of subgroups, or None if the group does not exist."""
        name = self._session.execute(
            text(GROUP_NAME_SQL), {"group_id": group_id}
        ).scalar_one_or_none()
        if name is None:
            return None
        papers = self._matched_papers(group_id)
        subgroups = order_subgroups(build_subgroups(papers, self._corpus_mean()), order)
        visible, total_pages = page_of(subgroups, page, page_size)
        return GroupPaperPage(
            group_id=group_id,
            group_name=name,
            order=order,
            page=page,
            page_size=page_size,
            total_subgroups=len(subgroups),
            total_papers=len(papers),
            total_pages=total_pages,
            subgroups=self._with_cards(visible),
        )

    def _matched_papers(self, group_id: int) -> list[MatchedPaper]:
        rows = self._session.execute(
            text(GROUP_PAPERS_SQL),
            {"group_id": group_id, "final_stage": PaperStageRun.FINAL_STAGE},
        )
        return [
            MatchedPaper(
                paper_id=row.paper_id,
                match_count=row.match_count,
                embedding=_as_array(row.mean_embedding),
            )
            for row in rows
        ]

    def _corpus_mean(self) -> Optional[np.ndarray]:
        return _as_array(self._session.execute(text(CORPUS_MEAN_SQL)).scalar_one_or_none())

    def _with_cards(self, subgroups: Sequence[list[MatchedPaper]]) -> list[PaperSubgroup]:
        """Preview cards for this page's papers only, in subgroup order."""
        ids = [paper.paper_id for group in subgroups for paper in group]
        cards = imported_papers_by_ids(self._session, ids)
        return [
            PaperSubgroup(
                size=len(group),
                papers=[
                    GroupPaper(**cards[paper.paper_id].model_dump(), match_count=paper.match_count)
                    for paper in group
                    # Absent only if the paper was removed since the first query.
                    if paper.paper_id in cards
                ],
            )
            for group in subgroups
        ]


def _as_array(values: Optional[Sequence[float]]) -> Optional[np.ndarray]:
    return None if values is None else np.asarray(values, dtype=np.float64)
