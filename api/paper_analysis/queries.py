"""SQL for paper analysis, kept apart from the manager that runs it.

Candidate paragraphs are prose only: `paragraph` and `abstract` passages in
the body sections. Headings, captions and tables are excluded, and so are
sections like abbreviation lists, which are nothing but entity names and
would otherwise win every mention count.
"""

from __future__ import annotations

#: Passage kinds that are prose.
PROSE_CHUNK_TYPES = ["paragraph", "abstract"]

#: Sections whose prose says something about the findings.
PROSE_SECTIONS = ["ABSTRACT", "INTRO", "METHODS", "RESULTS", "DISCUSS", "CONCL", "CASE"]

#: Mentions per (paragraph, term) in the selected papers. Term indexes travel
#: with each entity id, as in `api.paper_search.queries.ENTITY_HITS_SQL`.
PARAGRAPH_ENTITY_HITS_SQL = """
WITH terms AS (
    SELECT *
    FROM unnest(CAST(:term_indexes AS int[]), CAST(:entity_ids AS bigint[]))
        AS t(term_index, entity_id)
)
SELECT c.paper_id, c.id AS chunk_id, terms.term_index, count(*) AS hits
FROM paper_entity_mentions m
JOIN terms ON terms.entity_id = m.entity_id
JOIN paper_chunks c ON c.id = m.chunk_id
WHERE m.paper_id = ANY(CAST(:paper_ids AS bigint[]))
  AND c.chunk_type = ANY(CAST(:chunk_types AS text[]))
  AND c.section_type = ANY(CAST(:section_types AS text[]))
GROUP BY c.paper_id, c.id, terms.term_index
"""

#: `ts_rank` per (paragraph, phrase) in the selected papers. Term indexes are
#: 0-based positions in `:phrases`.
PARAGRAPH_TEXT_HITS_SQL = """
WITH terms AS (
    SELECT t.term_index - 1 AS term_index, phraseto_tsquery('english', t.phrase) AS query
    FROM unnest(CAST(:phrases AS text[])) WITH ORDINALITY AS t(phrase, term_index)
)
SELECT c.paper_id, c.id AS chunk_id, terms.term_index,
       ts_rank(c.text_search, terms.query) AS hits
FROM terms
JOIN paper_chunks c ON c.text_search @@ terms.query
WHERE c.paper_id = ANY(CAST(:paper_ids AS bigint[]))
  AND numnode(terms.query) > 0
  AND c.chunk_type = ANY(CAST(:chunk_types AS text[]))
  AND c.section_type = ANY(CAST(:section_types AS text[]))
"""

#: Cosine similarity of every pair among the candidates, computed in Postgres
#: so the vectors never leave it. Chunks without an embedding pair with nothing.
PARAGRAPH_SIMILARITIES_SQL = """
SELECT a.id AS a_id, b.id AS b_id, 1 - (a.embedding <=> b.embedding) AS similarity
FROM paper_chunks a
JOIN paper_chunks b ON a.id < b.id
WHERE a.id = ANY(CAST(:chunk_ids AS bigint[]))
  AND b.id = ANY(CAST(:chunk_ids AS bigint[]))
  AND a.embedding IS NOT NULL
  AND b.embedding IS NOT NULL
"""

#: What a citation shows and where it points.
PARAGRAPHS_SQL = """
SELECT id AS chunk_id, paper_id, ordinal, section_type, text
FROM paper_chunks
WHERE id = ANY(CAST(:chunk_ids AS bigint[]))
"""
