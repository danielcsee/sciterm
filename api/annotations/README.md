# api/annotations

Durable, owner-scoped definitions created from highlighted chat or paper text.
Each row keeps a live source association plus a text quote/position selector so
the highlight can be re-anchored after reload.

`POST /define` creates annotations after the definition succeeds. `GET
/annotations?chat_id=…` and `GET /annotations?paper_id=…` read them. Chat
annotations are also returned with a saved chat.

`models.py` defines the table, `schemas.py` the wire contracts, `queries.py`
the runtime SQL, `manager.py` ownership and source validation, and `routes.py`
the authenticated read endpoint.

Dependencies: `api.auth`, `api.chats`, `api.db`, FastAPI, Pydantic, and
SQLAlchemy.
