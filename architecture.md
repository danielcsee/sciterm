# Project Architecture

This project is a scientific-paper search and analysis system. FastAPI exposes the API, Celery imports and enriches papers in the background, PostgreSQL stores the corpus and its search indexes, and the React/TypeScript UI consumes both ordinary REST responses and streamed RAG results.

The core data flow is:

```text
PubTator / NCBI
      |
      v
FastAPI /import -> Celery ingest_paper -> PostgreSQL source data and chunks
                                  |
                                  v
                         Celery embed_paper
                                  |
                                  v
                   chunk, entity, and mention vectors

User query -> entity candidate retrieval -> LLM intent/entity resolution
                                              |
                           +------------------+-------------------+
                           |                                      |
                    paper_search                         paper_analysis
                           |                                      |
                     ranked papers              ranked papers -> evidence
                                                                  |
                                                                  v
                                                        streamed cited answer
```

## Paper import with Celery

The authenticated `POST /import` route in [`api/ingestion/routes.py`](api/ingestion/routes.py) accepts PMIDs and queues one Celery chain per unique paper:

```text
ingest_paper(pmid) | embed_paper(paper_id)
```

Before queueing, the route reserves the paper and writes `pending` rows for both stages in `paper_stage_runs`. This makes an import visible immediately, prevents duplicate chains for papers already complete or in progress, and lets `GET /import/status` report durable progress from PostgreSQL instead of relying on Celery's expiring result backend. A forced import can override those guards.

### Ingest stage

`ingest_paper` in [`api/ingestion/tasks.py`](api/ingestion/tasks.py) performs the network- and database-heavy half of the pipeline:

1. Reserve or find the `papers` row and skip the stage when its fingerprint is already current.
2. Fetch the full PubTator document. A Redis document cache is checked first; cache failure is non-fatal. NCBI calls share a Redis-backed rate limiter.
3. Resolve missing canonical entity names outside the database transaction.
4. Normalize and persist the paper, raw PubTator JSON, authors, chunks, grounded entities, mentions, relations, and references.
5. Mark the ingest stage `done` and remove the now-redundant cached document.

Chunking is part of ingest because chunks are derived directly from PubTator passages and do not justify another broker hop. Concurrent imports use deterministic entity/mention/relation insertion order and conflict-safe entity inserts to reduce row-lock deadlocks. PostgreSQL serialization failures and deadlocks are treated as retryable races; fetch failures and other task failures are recorded in the stage ledger before Celery retries.

### Embedding stage

`embed_paper` is deliberately separate so CPU-heavy vector generation can be retried or rerun after a model change without fetching the paper again. It:

1. Reads the paper's chunk text from PostgreSQL.
2. Generates normalized 768-dimensional vectors and writes them to `paper_chunks.embedding`.
3. Generates vectors for the paper's canonical entity names and distinct mention surface forms.
4. Marks the final `embed` stage `done` using a fingerprint of the model name and vector dimension.

A paper is considered part of the searchable corpus only when its final `embed` stage is complete. Tasks pass only the integer `paper_id` through Redis; document bodies and vectors remain in PostgreSQL. The embedding model (`BAAI/bge-base-en-v1.5` by default) is loaded lazily once per worker process. Documents are embedded as plain text, while query embeddings use the BGE retrieval instruction prefix.

The Celery app uses Redis as broker and result backend. Local macOS development uses a non-forking `solo` worker because Metal-backed sentence-transformers cannot safely initialize in a forked child.

## LLM tools and query paths

The `/corpus/rag_search` pipeline in [`api/corpus/rag.py`](api/corpus/rag.py) is streamed as newline-delimited JSON. It emits raw and filtered entity candidates first, then the routed result and selected papers, followed by answer deltas and answer metadata for an analysis request.

### Routing

The query is split into noun phrases and contiguous three-token n-grams. Each fragment is embedded and passed through the entity-matching system described below. The filtered candidates and original query are then sent to the LLM in one required tool call. The strict Pydantic-backed tools in [`api/llm/tools.py`](api/llm/tools.py) are:

- `paper_search`: the user wants a list of relevant papers.
- `paper_analysis`: the user wants an explanation or synthesis grounded in the papers.
- `no_match`: neither literature operation fits.

The same tool call also selects which candidate entities the query actually names and returns their exact query phrases. Returned IDs are joined back to the supplied candidates; invented IDs and duplicate entities are discarded. If OpenAI is unavailable or routing fails, the application remains useful: it falls back to noun-phrase paper search rather than failing the whole request.

### Shared paper retrieval

Both `paper_search` and `paper_analysis` call [`api/paper_search/search.py`](api/paper_search/search.py). Retrieval chooses one of two paths:

- **Entity path:** when the LLM confirms entities, each distinct query phrase becomes one search term containing all entity IDs resolved from that phrase. Hits are mention counts per paper and term.
- **Full-text fallback:** when there are no confirmed entities, topical noun phrases become PostgreSQL `phraseto_tsquery` searches over `paper_chunks.text_search`. Stop-word-only phrases and request nouns such as “papers” or “studies” are ignored. Overly common terms are dropped unless that would remove every matched term.

Only papers whose `paper_stage_runs` final stage is `done` are eligible. For each term, document frequency produces a smoothed weight:

```text
IDF = ln(1 + corpus_size / papers_matching_term)
paper score = sum(IDF(term) * ln(1 + hits(term)))
```

Papers rank first by the number of distinct terms matched, then by weighted score and total hits. The final `top_k` slots deliberately mix relevance and coverage: the broadest-coverage paper is selected first, followed by the strongest paper for each term in rarest-term-first order, then remaining slots are filled from the overall rank. Each result includes its selection reasons, metadata, abstract, and its strongest matching chunks.

### `paper_search`

For `paper_search`, the shared retrieval result is the final substantive output. It returns ranked papers and evidence chunks but does not ask the LLM to synthesize an answer.

### `paper_analysis`

`paper_analysis` starts with the same ranked papers and search-term weights, then [`api/paper_analysis`](api/paper_analysis) builds a smaller evidence set:

1. Consider prose `paragraph` and `abstract` chunks only, restricted to substantive sections such as Abstract, Methods, Results, Discussion, and Conclusion.
2. Per paper, select the configured number of paragraphs with the most total hits (two by default).
3. Optionally add one paragraph that covers more distinct query terms than every density pick; ties use the paper search's IDF-weighted score.
4. Compare candidate chunk embeddings in PostgreSQL and greedily remove near-duplicates in paper-rank/pick order. The default cosine-similarity cutoff is `0.985`.
5. Number the remaining citations by paper rank and then by reading order within each paper.
6. Stream an LLM answer constrained to those numbered passages.

Evidence selection uses entity mention counts for entity search and PostgreSQL `ts_rank` for the full-text fallback. Citation gathering and database sessions finish before the slower LLM request begins. If evidence is absent or answer generation fails, citations and a structured error can still be returned.

After an answer finishes, the system runs entity matching over the generated text with a larger candidate allowance. A final LLM tool call confirms which candidates the answer actually names and the exact phrases that name them, enabling entity annotations without delaying the streamed answer.

## Database schema and embeddings

The primary corpus schema is defined in [`api/db/models.py`](api/db/models.py). Its central relationships are:

```text
papers
  |-- paper_pubtator_docs       raw, lossless upstream response
  |-- paper_authors
  |-- paper_chunks              retrieval units, full-text index, embeddings
  |-- paper_entity_mentions ---- entities
  |-- paper_relations ---------- entities (subject and object)
  |-- paper_references
  `-- paper_stage_runs          durable ingest/embed ledger

entity_mention_embeddings ----- distinct mention text vectors
                ^
                `-- joined to entities through paper_entity_mentions.surface_text
```

Important schema choices include:

- `papers.pmid` is the natural key because PubTator is PMID-based; `pmcid` is optional for abstract-only papers.
- `paper_pubtator_docs` retains the original JSON so parsing or chunking can be changed without another rate-limited fetch.
- `paper_chunks` stores document offsets, section/type metadata, text, a generated English `tsvector`, and a nullable vector. The `tsvector` has a GIN index; embeddings have an HNSW cosine index.
- `entities` represents ontology-grounded concepts, uniquely identified by namespaced identifiers such as `MESH:D002118` or `ncbi_gene:672`. Surface text is not identity.
- `paper_entity_mentions` links an entity occurrence to a paper and, where resolvable, to a chunk. It preserves offsets and the observed wording.
- `paper_relations` stores typed, optionally scored subject/object assertions. `paper_references` stores citation metadata.
- `paper_stage_runs` has one row per paper and pipeline stage, including status, attempts, timestamps, errors, and an input fingerprint.

Authentication, saved chats, and entity groups use the same SQLAlchemy base and Alembic migration chain but are owned by feature-specific schemas in `api/auth/models.py`, `api/chats/models.py`, and `api/groups/models.py`.

### How embeddings are used

All stored vectors currently have 768 dimensions and use normalized sentence-transformer output with pgvector cosine distance:

| Vector location | Represents | Used for |
|---|---|---|
| `paper_chunks.embedding` | A paper retrieval chunk | Near-duplicate removal among analysis evidence paragraphs |
| `entities.embedding` | An entity's canonical name | Semantic entity candidate retrieval |
| `entity_mention_embeddings.embedding` | One distinct, case-sensitive mention surface form | Semantic matching against terminology as it appeared in papers |

Entity-name and mention vectors are derived data and are refreshed during the embedding stage; a backfill command can populate them for an existing corpus. Mention vectors are stored once per distinct surface form, then joined through `paper_entity_mentions` to all entities observed under that wording. HNSW indexes using `vector_cosine_ops` support nearest-neighbor candidate queries. There is intentionally no paper-level embedding: the design stores expensive upstream data and recomputes locally derivable representations when needed.

Embeddings do not currently rank papers directly. Paper ranking is driven by grounded entity mention counts or PostgreSQL full-text hits. Chunk vectors support analysis de-duplication, while entity and mention vectors support query-to-entity matching.

## Entity matching

Entity matching combines complementary retrieval methods and defers contextual disambiguation to the LLM. It does not collapse incomparable scores into one global numeric rank.

### 1. Extract overlapping query fragments

[`api/entity_matching/extraction.py`](api/entity_matching/extraction.py) uses spaCy to extract noun phrases followed by contiguous three-token n-grams. Duplicates are removed within each extraction method. The two extraction modes provide precise grammatical spans plus a fallback for phrases the parser does not expose as noun chunks.

### 2. Search four matcher/source combinations

For every fragment, `EntityMatchManager` independently queries:

| Matcher | Source | Purpose |
|---|---|---|
| Trigram | Canonical `entities.name` | Find lexical name matches and misspellings |
| Trigram | `paper_entity_mentions.surface_text` | Find lexical matches to observed aliases and wording |
| Embedding | Canonical `entities.embedding` | Find semantically similar canonical names |
| Embedding | `entity_mention_embeddings.embedding` | Find semantic matches to observed aliases and wording |

PostgreSQL `pg_trgm` first retrieves trigram candidates, but their scores are replaced with normalized, case-insensitive Levenshtein similarity before the final top-k cut. Trigrams are effective candidate generators for typos, while edit distance gives a more intuitive final lexical score. Embedding candidates use `1 - cosine_distance` and an HNSW index.

Mention-source queries may retrieve more rows before deduplication because the same surface form can occur repeatedly and can map to more than one grounded entity. Within a search path, duplicate `(entity_id, matched_text)` pairs are removed without disturbing score order.

### 3. Filter within strategies

Every extraction/matcher/source path remains observable as a separate group. Groups are then pooled by strategy (for example, noun-phrase + embedding + canonical name) across query fragments. Within each strategy the system:

1. Keeps the best-scoring candidate for each lowercased matched text.
2. Sorts candidates by score.
3. Retains at most one candidate per query word, capped at five by default.
4. Applies a matcher-specific cutoff (`0.8` normalized edit similarity for trigram and `0.65` cosine similarity for embeddings by default).

Lexical and embedding scores are intentionally not compared directly because they have different scales. Keeping strategy groups separate also makes it possible to inspect which extraction method, matcher, and text source surfaced a candidate.

### 4. Let the LLM resolve context

Candidates are deduplicated by entity ID for the intent request, while retaining every matched wording and strategy that surfaced each entity. The LLM sees the original query plus candidate IDs, canonical names, types, and matched texts. It selects only the entities actually referred to in context while simultaneously choosing `paper_search`, `paper_analysis`, or `no_match`. Application code rejects IDs outside the candidate set and deduplicates accepted entities.

The effective best match is therefore the result of layered evidence:

```text
phrase extraction
    -> lexical and semantic candidate retrieval
    -> source-aware, strategy-specific ranking and cutoffs
    -> entity-level candidate merge
    -> LLM contextual confirmation
```

This combination gives lexical matching authority on exact names and typos, embeddings reach paraphrases and aliases, mention text connects user language to corpus terminology, and the LLM handles ambiguity that string or vector similarity alone cannot resolve.

### Type-ahead variation

Smart Group type-ahead uses the same trigram and embedding candidate sources but adds a prefix matcher first. Prefix matching searches canonical names and mention forms sharing the first letter, ranks by typo-tolerant distance to the beginning of the candidate, and allows one edit for three-to-five characters or two edits for longer inputs. Suggestions are merged by fixed strategy priority—prefix first, then trigram and embedding paths—with one result per entity, because scores from those strategies are not comparable.
