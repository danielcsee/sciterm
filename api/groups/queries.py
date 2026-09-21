"""SQL for entity groups, kept apart from the manager that runs it."""

from __future__ import annotations

#: Every group with its entities in chip order, newest group first. One row per
#: member; a group whose entities were all deleted still appears, with one row
#: of null entity columns.
#:
#: `surface_text` is the corpus's commonest wording for an entity, fetched only
#: when its canonical name is missing or is really the identifier — Species
#: arrive named "9606". It is the same fallback `PaperEntities` uses, so a chip
#: reads the same on a tile as in a paper. `:group_id` narrows to one group.
GROUPS_SQL = """
SELECT g.id AS group_id, g.name AS group_name, g.created_at, g.updated_at,
       e.id AS entity_id, e.identifier, e.entity_type, e.database,
       e.name AS entity_name, surface.surface_text
FROM entity_groups g
LEFT JOIN entity_group_members m ON m.group_id = g.id
LEFT JOIN entities e ON e.id = m.entity_id
LEFT JOIN LATERAL (
    SELECT pem.surface_text
    FROM paper_entity_mentions pem
    WHERE pem.entity_id = e.id
      AND pem.surface_text IS NOT NULL
      AND (e.name IS NULL
           OR e.name = substring(e.identifier FROM position(':' IN e.identifier) + 1))
    GROUP BY pem.surface_text
    ORDER BY count(*) DESC, pem.surface_text
    LIMIT 1
) surface ON true
WHERE CAST(:group_id AS bigint) IS NULL OR g.id = CAST(:group_id AS bigint)
ORDER BY g.created_at DESC, g.id DESC, m.position
"""

INSERT_GROUP_SQL = """
INSERT INTO entity_groups (name) VALUES (:name) RETURNING id
"""

#: A null `:name` keeps the current one; the timestamp moves either way, since
#: a members-only edit is still an edit.
UPDATE_GROUP_SQL = """
UPDATE entity_groups
SET name = COALESCE(CAST(:name AS text), name), updated_at = now()
WHERE id = :group_id
RETURNING id
"""

DELETE_GROUP_SQL = """
DELETE FROM entity_groups WHERE id = :group_id RETURNING id
"""

DELETE_MEMBERS_SQL = """
DELETE FROM entity_group_members WHERE group_id = :group_id
"""

#: Positions are 0-based and follow the order of `:entity_ids`.
INSERT_MEMBERS_SQL = """
INSERT INTO entity_group_members (group_id, entity_id, position)
SELECT :group_id, t.entity_id, t.ordinal - 1
FROM unnest(CAST(:entity_ids AS bigint[])) WITH ORDINALITY AS t(entity_id, ordinal)
"""

#: The requested ids that name no entity, so a bad id is a 422 naming it rather
#: than a foreign-key error.
MISSING_ENTITIES_SQL = """
SELECT t.entity_id
FROM unnest(CAST(:entity_ids AS bigint[])) AS t(entity_id)
WHERE NOT EXISTS (SELECT 1 FROM entities e WHERE e.id = t.entity_id)
"""
