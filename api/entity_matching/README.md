# api/entity_matching

Experimental candidate generation for chat queries. `extraction.py` uses the
spaCy English dependency parser to emit noun phrases and contiguous three-word
ngrams. `search.py` independently searches canonical entity names and observed
mention surface text through PostgreSQL trigram and pgvector indexes.

Every extraction/matcher/source combination remains a separate response group
so retrieval quality can be inspected. Identifiers are returned as metadata but
are deliberately not searched.

`filtering.py` reduces those raw groups to `filtered_entity_matches`: per
strategy (pooled across fragments) it dedupes on lowercased matched text,
keeping the best score, keeps the top five (or one per query word for shorter
queries), then drops anything under 0.65.

Mention vectors live in `entity_mention_embeddings` rather than widening the
source annotation table. The table stores one vector per distinct,
case-sensitive `surface_text`; retrieval joins the form back to the distinct
entities associated with it through `paper_entity_mentions`.

Dependencies: spaCy with `en_core_web_sm`, SQLAlchemy, PostgreSQL `pg_trgm`,
and pgvector.
