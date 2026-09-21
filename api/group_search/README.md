# api/group_search

Paper search by entity group: every imported paper mentioning any of a
group's entities, clustered into subgroups whose papers discuss similar
topics.

```
GET /groups/{id}/papers?order=desc&page=1&page_size=10  ->  GroupPaperPage
```

`order` sorts subgroups by size (`desc`, the default, is largest first).
Papers inside a subgroup are sorted by how many **distinct** group entities
they mention. A page holds whole subgroups (`page_size` counts subgroups), so
a subgroup is never split across pages.

## Files

| File | Purpose |
|---|---|
| `queries.py` | SQL: matched papers with mean embeddings; the corpus mean |
| `subgroups.py` | Clustering, ordering, and paging — pure functions |
| `manager.py` | `GroupSearchManager`, which runs the SQL and assembles a page |
| `schemas.py` | Response models |
| `routes.py` | The route above |

## How subgroups are made

Each paper's vector is the mean of its paragraph embeddings, computed in SQL
on every request, minus the corpus-wide mean. Centering matters: uncentred
paper means are all nearly alike. Agglomerative clustering (average linkage,
cosine) merges papers until no clusters are closer than `DISTANCE_CUTOFF`.
Nothing is stored, so newly ingested papers join subgroups on the next load.

Cost grows with the chunks in the group plus one pass over all chunks for the
corpus mean. If that becomes slow, store a per-paper mean at ingest.

## Dependencies

SQLAlchemy, numpy, scipy, `api.db`, and `api.corpus` for the preview cards.
