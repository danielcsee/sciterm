# api/chats

Saved AI conversations, scoped to the authenticated admin account or the
redeemed access code that owns the session.

```
GET    /chats             -> saved-chat summaries
POST   /chats             -> create a chat and its first turn
GET    /chats/{id}        -> messages, citations, entity pills and annotations
POST   /chats/{id}/turns  -> append a user message and pending assistant message
DELETE /chats/{id}        -> delete it
```

The first submitted message creates the chat automatically. Each later turn is
appended atomically, and the RAG pipeline writes results, citations, answers and
entity pills in short transactions before streaming the completed artifact to
the browser. Citations and pills retain live foreign keys plus display
snapshots, so a saved answer still renders when metadata changes.

Experimental entity-match/debug output is deliberately not accepted by the
request schema and is never persisted.

## Files

- `models.py` — SQLAlchemy metadata for the four chat tables.
- `queries.py` — runtime SQL constants.
- `manager.py` — ownership resolution and incremental persistence.
- `persistence.py` — server-side RAG artifact writer.
- `schemas.py` — validated request and response contracts.
- `routes.py` — authenticated REST routes.

## Dependencies

FastAPI, Pydantic, SQLAlchemy, `api.auth`, `api.db`, and the existing paper and
entity tables.
