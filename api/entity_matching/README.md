# api/entity_matching

Entity candidates for chat queries and the Smart Groups type-ahead.

**Chat.** `extraction.py` emits noun phrases and three-word ngrams (spaCy).
`search.py` matches each against canonical names and mention surface text,
by trigram and by pgvector. Every extraction/matcher/source path stays a
separate group so retrieval can be inspected. Identifiers are not searched.

Trigram scores are harsh on typos, so `rescoring.py` replaces them with
`1 - levenshtein / longer length` before the top-k cut. `filtering.py` then
pools each strategy, dedupes, keeps the top five (one per word for shorter
queries; `max_per_strategy` raises it for longer text) and applies the per-matcher cutoffs in `cutoffs.toml`, validated by
`cutoffs.py` at startup.

**Type-ahead.** `suggest.py` merges one candidate per entity by strategy
priority, since the scores share no scale. First come `prefix.py`'s matches:
the fewest edits (an adjacent swap counts as one) from the input to the start
of a name — up to 1 edit for 3–5 characters, 2 beyond. This is candidate
finding, not rescoring: "brac" scores 0.22 against BRCA1, under the trigram
threshold. `prefix_search.py` fetches names and mention forms sharing the
first letter through `lower(...) text_pattern_ops` indexes. The raw trigram and
embedding groups follow.

Mention vectors live in `entity_mention_embeddings`, one per distinct surface
form, joined back to entities through `paper_entity_mentions`.

Dependencies: spaCy with `en_core_web_sm`, SQLAlchemy, PostgreSQL `pg_trgm`,
pgvector, and `tomli` on Python < 3.11.
