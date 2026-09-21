# api/entity_matching

Experimental candidate generation for chat queries. `extraction.py` uses the
spaCy English dependency parser to emit noun phrases and contiguous three-word
ngrams. `search.py` independently searches canonical entity names and observed
mention surface text through PostgreSQL trigram and pgvector indexes.

Every extraction/matcher/source combination remains a separate response group
so retrieval quality can be inspected. Identifiers are returned as metadata but
are deliberately not searched.

Trigram retrieval finds typos but scores them harshly (one wrong letter can
cost three trigrams), so `rescoring.py` replaces each trigram candidate's score
with normalised edit similarity, `1 - levenshtein / longer length`, before the
top-k cut. Embedding candidates keep their cosine score.

`filtering.py` reduces those raw groups to `filtered_entity_matches`: per
strategy (pooled across fragments) it dedupes on lowercased matched text,
keeping the best score, keeps the top five (or one per query word for shorter
queries), then drops anything under that matcher's cutoff. The cutoffs live in
`cutoffs.toml`, one per matcher because the scores are on different scales;
`cutoffs.py` validates the file and the API reads it once at startup.

`suggest.py` serves the Smart Groups type-ahead (`/entities/suggest`). The
chat filter's per-word limit and whole-word cutoffs reject partial input, so
it instead merges the manager's raw groups one candidate per entity, in
strategy priority order — trigram before embedding, names before mentions —
since the two score scales cannot be sorted together.

Mention vectors live in `entity_mention_embeddings` rather than widening the
source annotation table. The table stores one vector per distinct,
case-sensitive `surface_text`; retrieval joins the form back to the distinct
entities associated with it through `paper_entity_mentions`.

Dependencies: spaCy with `en_core_web_sm`, SQLAlchemy, PostgreSQL `pg_trgm`,
pgvector, and `tomli` on Python < 3.11.
