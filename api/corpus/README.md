# api/corpus

Reads over papers that finished importing.

```
GET /corpus?page=1&page_size=20   ->  CorpusPage        (the listing)
GET /corpus/rag_search?query=...  ->  NDJSON stream     (candidates, papers, answer, its entities)
GET /corpus/{paper_id}            ->  CorpusPaperDetail (one whole paper)
GET /corpus/{paper_id}/references ->  ReferenceList     (importable refs)
GET /corpus/{paper_id}/imported-references -> ImportedReferenceList (local citing papers)
GET /corpus/{paper_id}/entities   ->  PaperEntityList   (concepts + spans)
```

Read-only: `api.ingestion` writes these tables, this package reads them.

## Files

| File | Purpose |
|---|---|
| `routes.py` | The GET routes: paging and validation |
| `rag.py` | The chat pipeline behind `rag_search`, one NDJSON line per stage |
| `queries.py` | Listing, detail and reference reads |
| `models.py` | Response models for all four |

## Decisions worth knowing

**"Imported" means the final stage is done.** Routes join `paper_stage_runs`,
not `papers`: a row exists there from the moment `/import` reserves one.

**Route order matters.** `rag_search` is registered before
`/corpus/{paper_id}`, since FastAPI matches in order and "rag_search" against
an `int` path parameter is a 422.

**`/references` must request full text.** The light export reports
`pmcid: null` even for papers that *are* in PMC — it only appears when full
text is actually returned — so nothing cheaper can decide whether a reference
exists as a full Paper. A reference qualifies on `pmcid` **and** body passages.
Only references carrying a PMID can be asked about at all (0–93% of them,
measured). Everything returned is importable, so the UI's count is exact.

**`/imported-references` is the inverse, local edge.** It joins a paper's PMID
against `paper_references.ref_pmid` and returns only citing papers whose final
import stage is done. It never calls PubTator and does not require the access
gate.

**Chat search is routed first.** `rag_search` matches entity candidates for
the query's fragments and filters them. It then asks `api.llm` which tool the
query calls for and which candidates it names. `paper_search` and
`paper_analysis` both run `api.paper_search`, and `no_match` returns no
papers. `paper_analysis` then fills `analysis` via `api.paper_analysis`: a
cited answer, and the paragraphs it cites.

**`rag_search` streams each stage as it finishes** (`rag.py`):
`entity_matches` before OpenAI is asked anything, then `result` (everything
but the answer, citations included), then `answer_delta` lines and one
`answer_done`, and last `answer_entities`. That last stage reruns the query's
entity matching over the finished answer, with twice the candidate cap, and
OpenAI confirms every phrase naming each entity; it waits for the answer so it
never holds it up. Event models are in `models.py`. When routing is unconfigured or fails, the search still runs on noun
phrases and `intent_error` explains what happened. The OpenAI call and the
paper search use separate DB sessions, so no connection waits on OpenAI.

## Dependencies

`api.db`, `api.pb_client`, `api.ncbi`, `api.ingestion.embedding`, `api.entity_matching`, `api.llm`, `api.paper_search`, `api.paper_analysis`, `fastapi`, `pydantic`.
