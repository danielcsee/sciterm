"""SQL for group paper search, kept apart from the manager that runs it."""

from __future__ import annotations

#: Every imported paper mentioning at least one of the group's entities, with
#: how many distinct group entities it mentions and the mean of its paragraph
#: embeddings. Distinct entities, not mentions: a raw mention count favours
#: long papers. The mean is null for a paper with no embedded chunks.
#:
#: `real[]` rather than `vector` so the driver returns plain floats without
#: registering pgvector's type adapter.
GROUP_PAPERS_SQL = """
WITH matches AS (
    SELECT pem.paper_id, count(DISTINCT pem.entity_id) AS match_count
    FROM entity_group_members m
    JOIN paper_entity_mentions pem ON pem.entity_id = m.entity_id
    JOIN paper_stage_runs r
      ON r.paper_id = pem.paper_id AND r.stage = :final_stage AND r.status = 'done'
    WHERE m.group_id = :group_id
    GROUP BY pem.paper_id
)
SELECT matches.paper_id, matches.match_count,
       CAST(avg(c.embedding) AS real[]) AS mean_embedding
FROM matches
LEFT JOIN paper_chunks c ON c.paper_id = matches.paper_id AND c.embedding IS NOT NULL
GROUP BY matches.paper_id, matches.match_count
"""

#: The average of every paper's mean embedding, each paper weighted equally so
#: a long paper does not pull the centre toward itself. Subtracted before
#: clustering: paper means all lean the same way, so uncentred they look alike.
CORPUS_MEAN_SQL = """
SELECT CAST(avg(paper_mean) AS real[])
FROM (
    SELECT avg(embedding) AS paper_mean
    FROM paper_chunks
    WHERE embedding IS NOT NULL
    GROUP BY paper_id
) means
"""

GROUP_NAME_SQL = """
SELECT name FROM entity_groups WHERE id = :group_id
"""
