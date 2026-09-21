# api/paper_analysis

Answers a `paper_analysis` chat query in prose, citing the paragraphs it was
drawn from.

```
paper_search result -> paragraph hits -> select per paper -> drop near-copies -> number -> OpenAI -> answer
```

## Algorithm

Candidates are **prose paragraphs** only (`paragraph`/`abstract` passages in
Abstract, Intro, Methods, Results, Discussion, Conclusion, Case). Abbreviation
lists, captions and headings would otherwise win on mention density.

**Per paper:** the 2 paragraphs with the most hits summed over *all* query
terms, then one more for breadth. It must match the most distinct terms, ties
broken by Σ IDF × ln(1 + hits), using the search's own IDF weights. The breadth
paragraph is kept only if it matches more terms than both dense picks.

**De-duplication:** candidates are taken in paper rank then pick order, and one
whose cosine similarity to a kept paragraph is ≥ 0.985 is dropped: distinct
results in a shared template measured up to 0.98.

**Numbering:** grouped by paper in rank order, reading order within a paper.

The full-text path has no mentions, so it uses `ts_rank`, and nothing is
highlighted.

## Files

| File | Purpose |
|---|---|
| `evidence.py` | `gather_evidence`: select, de-duplicate, number |
| `selection.py` | Pure paragraph scoring and picks |
| `dedupe.py` | Pure near-duplicate rejection |
| `answer.py` | `answer_question`: prompts OpenAI, never raises |
| `manager.py` / `queries.py` | `ParagraphManager` and its SQL |
| `models.py` | Internal and response types |

## Dependencies

`api.paper_search`, `api.llm`, `api.db`, pgvector (`<=>`), Postgres full-text search.
