# api

The Python backend: a FastAPI server that fetches scientific papers from NCBI
and stores them in Postgres for retrieval.

It is a package rooted at the repository root, so imports and the ASGI target
are fully qualified — `uvicorn api.app.main:app`, not `main:app`. Run it via
[`scripts/dev.sh`](../scripts) rather than by hand; that script also starts the
datastores and applies migrations.

## Subdirectories

| Directory | Purpose |
|---|---|
| [`app/`](app) | FastAPI application object, lifespan wiring, and `Settings` |
| `redis_conn.py` | One async Redis connection per event loop, shared by both users |
| [`cache/`](cache) | Redis cache of raw PubTator documents, keyed by PMID |
| [`ncbi/`](ncbi) | Shared HTTP plumbing for the NCBI clients: pool, rate limit, errors |
| [`pb_client/`](pb_client) | PubTator3: search and full annotated papers (`/pb`) |
| [`pm_client/`](pm_client) | PMC Open Access: downloads article files (`/pm`) |
| [`eu_client/`](eu_client) | E-utilities: names the concepts PubTator leaves unnamed |
| [`db/`](db) | SQLAlchemy models, session plumbing, and Alembic migrations |
| [`ingestion/`](ingestion) | Celery import pipeline and the `/import` routes |
| [`corpus/`](corpus) | Read-only `/corpus` listing of imported papers |
| [`entity_matching/`](entity_matching) | Entity candidates for chat queries |
| [`llm/`](llm) | OpenAI: routes chat queries to a tool, resolves entities |
| [`paper_search/`](paper_search) | Chooses chat's papers by entity coverage or full-text |

## Dependencies

Declared in `requirements.txt`:

- **fastapi** / **uvicorn** — HTTP server
- **pydantic-settings** — configuration from environment and `.env`
- **httpx** — async HTTP client for the NCBI calls
- **SQLAlchemy** 2.x / **alembic** / **psycopg** (v3) / **pgvector** — Postgres
- **celery[redis]** / **redis** — task queue, and the document cache
- **sentence-transformers** — local chunk embeddings (BAAI/bge-base-en-v1.5)
- **spaCy** / **en_core_web_sm** — noun-phrase extraction for entity candidates
- **openai** — intent routing for chat queries (needs `OPENAI_API_KEY`)
- **tomli** — reads entity-match cutoffs on Python < 3.11 (stdlib `tomllib` after)

Postgres and two Redis instances — broker and document cache — run in Docker
(`docker-compose.yml` at the root).

## Notes

`/import` runs end to end: it fetches a paper from PubTator, stores it chunked
with its authors, references, entities, mentions and relations, then embeds
every chunk.
