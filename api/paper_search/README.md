# api/paper_search

Chooses the papers chat returns for the `paper_search` and `paper_analysis`
tools.

```
confirmed entities -> mentions per (paper, term)   \
  (none confirmed?) -> noun phrases -> full-text hits -> IDF weights -> rank -> select top_k
```

## Algorithm

A **term** is one query phrase. Several entities resolved from one phrase count
as the same term, so synonyms add up instead of looking like broader coverage.

**Rank:** distinct terms matched first, then Σ IDF × ln(1 + hits), where
IDF = ln(1 + N / df).

**Select** `PAPER_SEARCH_TOP_K` slots: the broadest-coverage paper (ties broken
by mentions), then the top paper for each term (rarest term first), then fill
from the rank. Each result carries `selected_by`.

**Full-text fallback:** runs when OpenAI confirms no entities or routing fails.
Each noun phrase becomes a `phraseto_tsquery` over `paper_chunks.text_search`,
and a hit is one matching chunk. Phrases made only of stop words and request
nouns ("papers", "studies") are skipped. Phrases matching more than
`PAPER_SEARCH_MAX_TERM_FRACTION` of the corpus are dropped from scoring.

## Files

| File | Purpose |
|---|---|
| `search.py` | `search_papers`: picks the path and assembles the result |
| `terms.py` | Entities or noun phrases -> `SearchTerm`s |
| `ranking.py` | Pure IDF, scoring, and slot selection |
| `manager.py` | `PaperSearchManager`: runs the SQL |
| `queries.py` | SQL constants |
| `models.py` | Internal terms/hits and the response models |

## Dependencies

`api.db`, `api.entity_matching` (`QueryFragment`), `api.llm` (`IntentEntity`),
`spacy` stop words, Postgres full-text search.
