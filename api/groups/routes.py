"""Entity group CRUD, and the entity type-ahead that fills a group.

Ungated: groups are shared, and anyone may read and edit them. The type-ahead
runs one local embedding and four indexed queries, and never leaves the
machine, so it is ungated too.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Response

from api.app.config import get_settings
from api.db import session_scope
from api.entity_matching import (
    EntityMatch,
    EntityMatchGroup,
    EntityMatchManager,
    PrefixMatchManager,
    QueryFragment,
    merge_suggestions,
)
from api.entity_matching.suggest import SUGGESTION_LIMIT
from api.groups.manager import DuplicateGroupNameError, GroupManager
from api.groups.schemas import (
    MAX_SUGGEST_LENGTH,
    MIN_SUGGEST_LENGTH,
    CreateGroupRequest,
    EntityGroupList,
    EntityGroupOut,
    EntitySuggestions,
    SuggestedEntity,
    UpdateGroupRequest,
)
from api.ingestion.embedding import embed_queries

router = APIRouter(tags=["groups"])


@router.get("/groups", response_model=EntityGroupList, summary="List entity groups")
def list_groups() -> EntityGroupList:
    with session_scope() as session:
        return EntityGroupList(groups=GroupManager(session).list_groups())


@router.post(
    "/groups",
    response_model=EntityGroupOut,
    status_code=201,
    summary="Create an entity group",
)
def create_group(body: CreateGroupRequest) -> EntityGroupOut:
    try:
        with session_scope() as session:
            manager = GroupManager(session)
            _require_entities(manager, body.entity_ids)
            group_id = manager.create(body.name, body.entity_ids)
            return _read_back(manager, group_id)
    except DuplicateGroupNameError as exc:
        raise _duplicate_name(body.name) from exc


@router.patch(
    "/groups/{group_id}",
    response_model=EntityGroupOut,
    summary="Rename a group and/or replace its entities",
)
def update_group(
    body: UpdateGroupRequest, group_id: int = Path(..., ge=1)
) -> EntityGroupOut:
    try:
        with session_scope() as session:
            manager = GroupManager(session)
            if body.entity_ids is not None:
                _require_entities(manager, body.entity_ids)
            if not manager.update(group_id, body.name, body.entity_ids):
                raise _not_found(group_id)
            return _read_back(manager, group_id)
    except DuplicateGroupNameError as exc:
        raise _duplicate_name(body.name or "") from exc


@router.delete("/groups/{group_id}", status_code=204, summary="Delete an entity group")
def delete_group(group_id: int = Path(..., ge=1)) -> Response:
    with session_scope() as session:
        if not GroupManager(session).delete(group_id):
            raise _not_found(group_id)
    return Response(status_code=204)


@router.get(
    "/entities/suggest",
    response_model=EntitySuggestions,
    summary="Type-ahead entity candidates for a partial name",
)
def suggest_entities(
    q: str = Query(..., min_length=MIN_SUGGEST_LENGTH, max_length=MAX_SUGGEST_LENGTH),
) -> EntitySuggestions:
    """Typo-tolerant prefix matches, then the chat's four candidate strategies.

    The whole input is one fragment: spaCy extraction exists to split a
    sentence into phrases, and a type-ahead box already holds one phrase. The
    extraction label is required by `QueryFragment` but unused here.
    """
    query = q.strip()
    if len(query) < MIN_SUGGEST_LENGTH:
        return EntitySuggestions(query=query)
    prefix_matches, groups = _match_candidates(
        QueryFragment(text=query, method="noun_phrase")
    )
    return EntitySuggestions(
        query=query,
        entities=[
            SuggestedEntity(**match.model_dump(exclude={"score"}))
            for match in merge_suggestions(groups, prefix_matches)
        ],
    )


def _match_candidates(
    fragment: QueryFragment,
) -> tuple[list[EntityMatch], list[EntityMatchGroup]]:
    settings = get_settings()
    vectors = embed_queries([fragment.text])
    with session_scope() as session:
        prefix_matches = PrefixMatchManager(session).search(fragment.text, SUGGESTION_LIMIT)
        groups = EntityMatchManager(
            session,
            top_k=settings.entity_match_top_k,
            embedding_threshold=settings.entity_match_embedding_threshold,
            trigram_threshold=settings.entity_match_trigram_threshold,
        ).search([fragment], vectors)
    return prefix_matches, groups


def _require_entities(manager: GroupManager, entity_ids: list[int]) -> None:
    missing = manager.missing_entities(entity_ids)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"no such entities: {', '.join(map(str, missing))}"
        )


def _read_back(manager: GroupManager, group_id: int) -> EntityGroupOut:
    group = manager.get_group(group_id)
    if group is None:  # deleted between the write and the read
        raise _not_found(group_id)
    return group


def _not_found(group_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"group {group_id} does not exist")


def _duplicate_name(name: str) -> HTTPException:
    return HTTPException(
        status_code=409, detail=f"A group named “{name}” already exists."
    )
