"""Runtime SQL for saved chats."""

from __future__ import annotations

AUTH_SESSION_OWNER_SQL = """
SELECT free_access_code_id
FROM auth_sessions
WHERE id = :session_id
"""

LIST_CHATS_SQL = """
SELECT c.id AS chat_id, c.title, c.created_at, c.updated_at,
       count(m.id)::integer AS message_count,
       COALESCE(
           (array_agg(m.content ORDER BY m.ordinal)
            FILTER (WHERE m.role = 'user'))[1],
           ''
       ) AS preview
FROM ai_chats c
LEFT JOIN ai_chat_messages m ON m.chat_id = c.id
WHERE c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
GROUP BY c.id
ORDER BY c.updated_at DESC, c.id DESC
"""

GET_CHAT_SQL = """
SELECT id AS chat_id, title, created_at, updated_at
FROM ai_chats
WHERE id = :chat_id
  AND owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
"""

GET_MESSAGES_SQL = """
SELECT id, role, content, fallback_text, status, response_kind, result_papers,
       papers_considered, analysis_entity_ids, analysis_duplicates_rejected,
       analysis_model, analysis_error
FROM ai_chat_messages
WHERE chat_id = :chat_id
ORDER BY ordinal
"""

GET_CITATIONS_SQL = """
SELECT assistant_message_id, number, paper_id, chunk_id, paper_chunk_ordinal,
       paper_pmid_snapshot, paper_title_snapshot, section_type, quoted_text, selected_by
FROM ai_chat_citations
WHERE assistant_message_id = ANY(CAST(:message_ids AS uuid[]))
ORDER BY assistant_message_id, position
"""

GET_ENTITIES_SQL = """
SELECT assistant_message_id, entity_id, identifier_snapshot, entity_type_snapshot,
       name_snapshot, phrases
FROM ai_chat_message_entities
WHERE assistant_message_id = ANY(CAST(:message_ids AS uuid[]))
ORDER BY assistant_message_id, position
"""

GET_ANNOTATIONS_SQL = """
SELECT a.id, a.ai_chat_id, a.ai_chat_message_id, a.paper_id,
       pc.ordinal AS paper_chunk_ordinal, a.source_key, a.phrase,
       a.surrounding_context, a.definition, a.quote_exact, a.quote_prefix,
       a.quote_suffix, a.start_offset, a.end_offset, a.position,
       a.created_at, a.updated_at
FROM user_annotations a
LEFT JOIN paper_chunks pc ON pc.id = a.paper_chunk_id
WHERE a.ai_chat_id = :chat_id
ORDER BY a.position DESC
"""

INSERT_CHAT_SQL = """
INSERT INTO ai_chats (title, owner_user_id, owner_free_access_code_id)
VALUES (:title, :owner_user_id, :owner_code_id)
RETURNING id
"""

LOCK_CHAT_SQL = """
SELECT id
FROM ai_chats
WHERE id = :chat_id
  AND owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
FOR UPDATE
"""

CHAT_MESSAGE_OWNED_SQL = """
SELECT m.id
FROM ai_chat_messages m
JOIN ai_chats c ON c.id = m.chat_id
WHERE c.id = :chat_id AND m.id = CAST(:message_id AS uuid)
  AND c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
"""

NEXT_MESSAGE_ORDINAL_SQL = """
SELECT COALESCE(max(ordinal), -1) + 1
FROM ai_chat_messages
WHERE chat_id = :chat_id
"""

INSERT_MESSAGE_SQL = """
INSERT INTO ai_chat_messages (
    id, chat_id, ordinal, role, content, fallback_text, status, response_kind,
    result_papers, papers_considered, analysis_entity_ids,
    analysis_duplicates_rejected, analysis_model, analysis_error
) VALUES (
    CAST(:id AS uuid), :chat_id, :ordinal, :role, :content, :fallback_text,
    :status, :response_kind, CAST(:result_papers AS jsonb), :papers_considered,
    CAST(:analysis_entity_ids AS jsonb), :analysis_duplicates_rejected,
    :analysis_model, :analysis_error
)
"""

UPDATE_CHAT_TOUCHED_SQL = """
UPDATE ai_chats SET updated_at = now() WHERE id = :chat_id
"""

UPDATE_MESSAGE_RESULT_SQL = """
UPDATE ai_chat_messages m
SET content = :content, fallback_text = :fallback_text, status = 'done',
    response_kind = :response_kind, result_papers = CAST(:result_papers AS jsonb),
    papers_considered = :papers_considered,
    analysis_entity_ids = CAST(:analysis_entity_ids AS jsonb),
    analysis_duplicates_rejected = :analysis_duplicates_rejected,
    analysis_model = :analysis_model, analysis_error = :analysis_error
FROM ai_chats c
WHERE m.id = CAST(:message_id AS uuid) AND m.chat_id = :chat_id
  AND c.id = m.chat_id
  AND c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
RETURNING m.id
"""

UPDATE_MESSAGE_ANSWER_SQL = """
UPDATE ai_chat_messages m
SET content = COALESCE(:answer, ''), status = CASE WHEN :answer IS NULL THEN 'error' ELSE 'done' END,
    analysis_model = :model, analysis_error = :error
FROM ai_chats c
WHERE m.id = CAST(:message_id AS uuid) AND m.chat_id = :chat_id
  AND c.id = m.chat_id
  AND c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
RETURNING m.id
"""

FAIL_MESSAGE_SQL = """
UPDATE ai_chat_messages m
SET content = :error, fallback_text = NULL, status = 'error'
FROM ai_chats c
WHERE m.id = CAST(:message_id AS uuid) AND m.chat_id = :chat_id
  AND c.id = m.chat_id AND m.status = 'pending'
  AND c.owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND c.owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
RETURNING m.id
"""

DELETE_CITATIONS_SQL = """
DELETE FROM ai_chat_citations WHERE assistant_message_id = CAST(:message_id AS uuid)
"""

DELETE_ENTITIES_SQL = """
DELETE FROM ai_chat_message_entities WHERE assistant_message_id = CAST(:message_id AS uuid)
"""

INSERT_CITATION_SQL = """
INSERT INTO ai_chat_citations (
    assistant_message_id, number, position, paper_id, chunk_id,
    paper_chunk_ordinal, paper_pmid_snapshot, paper_title_snapshot,
    section_type, quoted_text, selected_by
) VALUES (
    CAST(:message_id AS uuid), :number, :position, :paper_id, :chunk_id,
    :paper_chunk_ordinal, :paper_pmid, :paper_title, :section_type,
    :quoted_text, :selected_by
)
"""

INSERT_ENTITY_SQL = """
INSERT INTO ai_chat_message_entities (
    assistant_message_id, position, entity_id, identifier_snapshot,
    entity_type_snapshot, name_snapshot, phrases
) VALUES (
    CAST(:message_id AS uuid), :position, :entity_id, :identifier,
    :entity_type, :name, CAST(:phrases AS jsonb)
)
"""

DELETE_CHAT_SQL = """
DELETE FROM ai_chats
WHERE id = :chat_id
  AND owner_user_id IS NOT DISTINCT FROM CAST(:owner_user_id AS bigint)
  AND owner_free_access_code_id IS NOT DISTINCT FROM CAST(:owner_code_id AS bigint)
RETURNING id
"""
