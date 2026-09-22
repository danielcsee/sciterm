# tests

Unit tests for the `api` package. Pure-logic only: no Postgres, Redis, or
network. Anything needing a live service belongs in an
integration suite instead, and is recorded in Testledger as a skip disposition
rather than left as a silent gap.

## Layout

One file per module under test, named for it:

| File | Covers |
| --- | --- |
| `test_chunking.py` | `api/ingestion/chunking.py` — passage-to-chunk conversion and offsets |
| `test_auth_tokens.py` | `api/auth/tokens.py` — JWT access tokens and opaque refresh tokens |
| `test_auth_passwords.py` | `api/auth/passwords.py` — PBKDF2 hashing and verification |
| `test_pb_models.py` | `api/pb_client/models.py` — PubTator identifier normalisation |
| `test_eu_naming.py` | `api/eu_client/naming.py` — the no-op and early-return paths |
| `test_persist.py` | `api/ingestion/persist.py` — the pure provenance and date rules |
| `test_ncbi_http.py` | `api/ncbi/http.py` — `RateLimiter`, the in-process 3/s budget |
| `test_auth_throttle.py` | `api/auth/throttle.py` — the pre-authentication sliding window |
| `test_entity_filtering.py` | `api/entity_matching/filtering.py` — per-strategy cuts and cutoffs |
| `test_entity_rescoring.py` | `api/entity_matching/rescoring.py` — edit-distance scoring |
| `test_entity_prefix.py` | `api/entity_matching/prefix.py` — typo-tolerant prefix distance and ranking |
| `test_entity_suggest.py` | `api/entity_matching/suggest.py` — type-ahead merge order |
| `test_entity_cutoffs.py` | `api/entity_matching/cutoffs.py` — loading and validating the TOML |
| `test_paper_analysis_answer.py` | `api/paper_analysis/answer.py` — when an answer is asked for, and how it ends |
| `test_llm_client.py` | `api/llm/client.py` — reading answer text out of a response stream |
| `test_llm_answer_entities.py` | `api/llm/answer_entities.py` — joining phrases back to candidates |

`conftest.py` puts the repository root on `sys.path`; the `api` package is run
from the checkout rather than installed.

## Dependencies

`pytest` and `coverage`, from `requirements-dev.txt`, installed into `.venv`.
Tests are discovered and run through Testledger, which is an external tool
pinned by `testledger.lock` and fetched on first use:

```sh
scripts/testledger.sh test --json
```

Running `pytest` directly works but records nothing in the ledger.
