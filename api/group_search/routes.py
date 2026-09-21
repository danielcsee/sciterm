"""The group paper search route.

Ungated, like the groups themselves: it reads local tables and runs a local
clustering, and never calls an external service.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from api.db import session_scope
from api.group_search.manager import GroupSearchManager
from api.group_search.schemas import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, GroupPaperPage
from api.group_search.subgroups import SortOrder

router = APIRouter(tags=["groups"])


@router.get(
    "/groups/{group_id}/papers",
    response_model=GroupPaperPage,
    summary="Papers mentioning a group's entities, in subgroups of similar topics",
)
def group_papers(
    group_id: int = Path(..., ge=1),
    order: SortOrder = Query("desc", description="Subgroup size: desc is largest first"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> GroupPaperPage:
    with session_scope() as session:
        result = GroupSearchManager(session).search(group_id, order, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail=f"group {group_id} does not exist")
    return result
