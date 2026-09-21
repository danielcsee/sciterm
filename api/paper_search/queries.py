"""SQL for paper search, kept apart from the manager that runs it.

Every query counts only papers whose final import stage is done, the same
membership rule as the rest of the corpus. Terms travel as parallel arrays and
are unnested server-side, so one statement serves any number of terms.
"""

from __future__ import annotations

#: Papers eligible to be searched: the `N` in each term's IDF.
CORPUS_SIZE_SQL = """
SELECT count(*)
FROM paper_stage_runs
WHERE stage = :final_stage AND status = 'done'
"""

#: Mentions per (paper, term). A term is a query phrase and may carry several
#: entity ids, so synonyms of one phrase add up rather than count as two terms.
ENTITY_HITS_SQL = """
WITH terms AS (
    SELECT *
    FROM unnest(CAST(:term_indexes AS int[]), CAST(:entity_ids AS bigint[]))
        AS t(term_index, entity_id)
)
SELECT m.paper_id, terms.term_index, count(*) AS hits
FROM paper_entity_mentions m
JOIN terms ON terms.entity_id = m.entity_id
JOIN paper_stage_runs s
    ON s.paper_id = m.paper_id AND s.stage = :final_stage AND s.status = 'done'
GROUP BY m.paper_id, terms.term_index
"""

#: Matching chunks per (paper, term). Each phrase is a phrase query, so its
#: words must be adjacent; a phrase of only stop words parses to an empty query
#: and is skipped rather than matched against everything.
TEXT_HITS_SQL = """
WITH terms AS (
    SELECT t.term_index - 1 AS term_index, phraseto_tsquery('english', t.phrase) AS query
    FROM unnest(CAST(:phrases AS text[])) WITH ORDINALITY AS t(phrase, term_index)
)
SELECT c.paper_id, terms.term_index, count(*) AS hits
FROM terms
JOIN paper_chunks c ON c.text_search @@ terms.query
JOIN paper_stage_runs s
    ON s.paper_id = c.paper_id AND s.stage = :final_stage AND s.status = 'done'
WHERE numnode(terms.query) > 0
GROUP BY c.paper_id, terms.term_index
"""

#: Each selected paper's chunks holding the most query-entity mentions.
ENTITY_CHUNKS_SQL = """
SELECT paper_id, chunk_id, section_type, text, score
FROM (
    SELECT c.paper_id, c.id AS chunk_id, c.section_type, c.text,
           count(*) AS score,
           row_number() OVER (PARTITION BY c.paper_id ORDER BY count(*) DESC, c.id) AS rank
    FROM paper_entity_mentions m
    JOIN paper_chunks c ON c.id = m.chunk_id
    WHERE m.paper_id = ANY(CAST(:paper_ids AS bigint[]))
      AND m.entity_id = ANY(CAST(:entity_ids AS bigint[]))
    GROUP BY c.paper_id, c.id, c.section_type, c.text
) ranked
WHERE rank <= :per_paper
ORDER BY paper_id, rank
"""

#: Each selected paper's chunks ranked by summed `ts_rank` over the phrases.
TEXT_CHUNKS_SQL = """
WITH terms AS (
    SELECT phraseto_tsquery('english', phrase) AS query
    FROM unnest(CAST(:phrases AS text[])) AS phrase
)
SELECT paper_id, chunk_id, section_type, text, score
FROM (
    SELECT c.paper_id, c.id AS chunk_id, c.section_type, c.text,
           sum(ts_rank(c.text_search, terms.query)) AS score,
           row_number() OVER (
               PARTITION BY c.paper_id
               ORDER BY sum(ts_rank(c.text_search, terms.query)) DESC, c.id
           ) AS rank
    FROM paper_chunks c
    JOIN terms ON c.text_search @@ terms.query
    WHERE c.paper_id = ANY(CAST(:paper_ids AS bigint[]))
      AND numnode(terms.query) > 0
    GROUP BY c.paper_id, c.id, c.section_type, c.text
) ranked
WHERE rank <= :per_paper
ORDER BY paper_id, rank
"""

#: Display metadata for the selected papers.
PAPER_METADATA_SQL = """
SELECT id, pmid, pmcid, title, journal, pub_year
FROM papers
WHERE id = ANY(CAST(:paper_ids AS bigint[]))
"""

#: Each paper's abstract prose in reading order. Structured abstracts arrive as
#: several chunks, with their headings ("Background") as `abstract_title_1`
#: chunks of their own; those are left out so the abstract reads as prose.
ABSTRACTS_SQL = """
SELECT paper_id, string_agg(text, ' ' ORDER BY ordinal) AS abstract
FROM paper_chunks
WHERE paper_id = ANY(CAST(:paper_ids AS bigint[]))
  AND section_type = 'ABSTRACT'
  AND coalesce(chunk_type, '') <> 'abstract_title_1'
GROUP BY paper_id
"""
