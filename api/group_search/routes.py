"""The group paper search routes: by saved group, or by an ad-hoc entity list.

Ungated, like the groups themselves: it reads local tables and runs a local
clustering, and never calls an external service.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from api.db import session_scope
from api.group_search.manager import GroupSearchManager
from api.group_search.schemas import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    EntityPaperPage,
    GroupPaperPage,
)
from api.group_search.subgroups import SortOrder
from api.groups.schemas import MAX_GROUP_ENTITIES, dedupe_ids

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


@router.get(
    "/entities/papers",
    response_model=EntityPaperPage,
    summary="Papers mentioning any of a set of entities, in subgroups of similar topics",
)
def entity_papers(
    entity_ids: list[int] = Query(
        ...,
        min_length=1,
        max_length=MAX_GROUP_ENTITIES,
        description="Repeat the parameter per entity: ?entity_ids=1&entity_ids=2",
    ),
    order: SortOrder = Query("desc", description="Subgroup size: desc is largest first"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> EntityPaperPage:
    ids = _valid_entity_ids(entity_ids)
    with session_scope() as session:
        return GroupSearchManager(session).search_entities(ids, order, page, page_size)


def _valid_entity_ids(values: list[int]) -> list[int]:
    """Deduplicated ids, or a 422 for a non-positive one."""
    try:
        return dedupe_ids(values)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
