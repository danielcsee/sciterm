"""Runtime SQL for user annotations."""

CHAT_SOURCE_SQL = """
SELECT m.id
FROM ai_chat_messages m
JOIN ai_chats c ON c.id = m.chat_id
WHERE c.id = :chat_id AND m.id = CAST(:message_id AS uuid)
  AND c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
"""

PAPER_CHUNK_SQL = """
SELECT id FROM paper_chunks
WHERE paper_id = :paper_id AND ordinal = :chunk_ordinal
"""

PAPER_EXISTS_SQL = "SELECT id FROM papers WHERE id = :paper_id"

NEXT_POSITION_SQL = """
SELECT COALESCE(max(position), -1) + 1
FROM user_annotations
WHERE ai_chat_id IS NOT DISTINCT FROM CAST(:chat_id AS bigint)
  AND paper_id IS NOT DISTINCT FROM CAST(:paper_id AS bigint)
  AND owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
"""

INSERT_ANNOTATION_SQL = """
INSERT INTO user_annotations (
    id, owner_user_id, owner_free_access_code_id, ai_chat_id,
    ai_chat_message_id, paper_id, paper_chunk_id, source_key, phrase,
    surrounding_context, definition, quote_exact, quote_prefix, quote_suffix,
    start_offset, end_offset, position
) VALUES (
    CAST(:id AS uuid), :owner_user_id, :owner_code_id, :chat_id,
    CAST(:message_id AS uuid), :paper_id, :paper_chunk_id, :source_key, :phrase,
    :surrounding_context, NULL, :quote_exact, :quote_prefix, :quote_suffix,
    :start_offset, :end_offset, :position
)
RETURNING created_at, updated_at
"""

SET_DEFINITION_SQL = """
UPDATE user_annotations
SET definition = :definition, updated_at = now()
WHERE id = CAST(:id AS uuid)
RETURNING updated_at
"""

LIST_ANNOTATIONS_SQL = """
SELECT a.id, a.ai_chat_id, a.ai_chat_message_id, a.paper_id,
       pc.ordinal AS paper_chunk_ordinal, a.source_key, a.phrase,
       a.surrounding_context, a.definition, a.quote_exact, a.quote_prefix,
       a.quote_suffix, a.start_offset, a.end_offset, a.position,
       a.created_at, a.updated_at
FROM user_annotations a
LEFT JOIN paper_chunks pc ON pc.id = a.paper_chunk_id
WHERE a.ai_chat_id IS NOT DISTINCT FROM CAST(:chat_id AS bigint)
  AND a.paper_id IS NOT DISTINCT FROM CAST(:paper_id AS bigint)
  AND a.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND a.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
ORDER BY a.position DESC
"""

DELETE_ANNOTATION_SQL = """
DELETE FROM user_annotations
WHERE id = CAST(:id AS uuid)
  AND owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
RETURNING id
"""
