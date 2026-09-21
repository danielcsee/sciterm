# api/groups

Entity groups: named, ordered sets of corpus entities, shared by everyone.

```
GET    /groups                  ->  EntityGroupList   (newest first)
POST   /groups                  ->  EntityGroupOut    201, 409 on a taken name
PATCH  /groups/{id}             ->  EntityGroupOut    name and/or entity_ids
DELETE /groups/{id}             ->  204
GET    /entities/suggest?q=...  ->  EntitySuggestions (type-ahead)
```

All ungated: groups have no owner; the type-ahead is local compute.
`GET /groups/{id}/papers`, the group's papers in subgroups, lives in
`api/group_search`.

## Files

| File | Purpose |
|---|---|
| `models.py` | `entity_groups` and `entity_group_members` tables |
| `queries.py` | SQL constants |
| `manager.py` | `GroupManager`, the only code that touches the tables |
| `schemas.py` | Request/response models and their validation |
| `routes.py` | The five routes above |

## Decisions worth knowing

**Names are unique ignoring case**, by a unique index on `lower(name)`. The
manager turns that index's violation into `DuplicateGroupNameError`, and the
route into a 409. Names are trimmed; blank ones are rejected.

**A group is never empty.** `entity_ids` needs at least one id, and repeats are
dropped keeping first-seen order, which is chip order (`position`).

**`PATCH` replaces the whole entity list** when `entity_ids` is given.

**Chip labels** follow `PaperEntities`: when an entity's name is really its
identifier (Species), `names` carries the corpus's commonest wording.

**Suggestions** are typo-tolerant prefix matches (`PrefixMatchManager`), then
`EntityMatchManager` with the typed text as one fragment, merged by
`entity_matching.merge_suggestions` rather than the chat filter — see
`api/entity_matching/suggest.py` for why.

## Dependencies

SQLAlchemy, `api.db`, `api.entity_matching`, and `api.ingestion.embedding`
for the query vector.
