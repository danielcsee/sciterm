# api/chats

Saved AI conversations, scoped to the authenticated admin account or the
redeemed access code that owns the session.

```
GET    /chats             -> saved-chat summaries
POST   /chats             -> create a complete chat snapshot
GET    /chats/{id}        -> messages, citations and entity pills
PUT    /chats/{id}        -> replace that snapshot
DELETE /chats/{id}        -> delete it
```

Messages are ordered and immutable inside a snapshot. Updating a chat replaces
its messages in one transaction, which prevents a reload from seeing citations
or pills from only half of an exchange. Citations and entity pills retain both
live foreign keys and display snapshots, so a saved answer still renders when
paper or entity metadata changes.

Experimental entity-match/debug output is deliberately not accepted by the
request schema and is never persisted.

## Files

- `models.py` — SQLAlchemy metadata for the four chat tables.
- `queries.py` — runtime SQL constants.
- `manager.py` — ownership resolution and transactional persistence.
- `schemas.py` — validated request and response contracts.
- `routes.py` — authenticated REST routes.

## Dependencies

FastAPI, Pydantic, SQLAlchemy, `api.auth`, `api.db`, and the existing paper and
entity tables.
