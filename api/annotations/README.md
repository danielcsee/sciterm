# api/annotations

Durable, owner-scoped definitions created from highlighted chat or paper text.
Each row keeps a live source association plus a text quote/position selector so
the highlight can be re-anchored after reload.

`POST /define` saves the annotation first, with a null definition, then fills
it in once OpenAI answers; a failed definition leaves the annotation saved. `GET
/annotations?chat_id=…` and `GET /annotations?paper_id=…` read them, and
`DELETE /annotations/{id}` removes one. Deleting a chat deletes its annotations. Chat
annotations are also returned with a saved chat.

`models.py` defines the table, `schemas.py` the wire contracts, `queries.py`
the runtime SQL, `manager.py` ownership and source validation, and `routes.py`
the authenticated read and delete endpoints.

Dependencies: `api.auth`, `api.chats`, `api.db`, FastAPI, Pydantic, and
SQLAlchemy.
