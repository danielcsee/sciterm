/**
 * Typed access to `/groups` and `/entities/suggest`, mirroring
 * `api/groups/schemas.py` — changing one means changing the other.
 */
import { ApiError } from '../api'
import { authFetch } from '../auth'

/** An entity in a group; the same fields `entityLabel` reads. */
export interface GroupEntity {
  entity_id: number
  identifier: string
  entity_type: string
  database: string
  name: string | null
  /** The corpus's commonest wording, only when `name` is really the id. */
  names: string[]
}

export interface EntityGroup {
  group_id: number
  name: string
  created_at: string
  updated_at: string
  entities: GroupEntity[]
}

interface EntityGroupList {
  groups: EntityGroup[]
}

export interface EntitySuggestion {
  entity_id: number
  identifier: string
  entity_type: string
  database: string
  name: string | null
  /** The name or mention text the typed input matched. */
  matched_text: string
}

interface EntitySuggestions {
  query: string
  entities: EntitySuggestion[]
}

/**
 * Characters typed before the box searches. The server accepts 2, but trigram
 * matches on two letters are mostly noise.
 */
export const MIN_TYPEAHEAD_LENGTH = 3

/**
 * A suggestion as a group member. The matched text stands in for the corpus
 * wording, so a Species picked by typing "cat" reads "cat", not "9685".
 */
export function suggestionToEntity(suggestion: EntitySuggestion): GroupEntity {
  return {
    entity_id: suggestion.entity_id,
    identifier: suggestion.identifier,
    entity_type: suggestion.entity_type,
    database: suggestion.database,
    name: suggestion.name,
    names: [suggestion.matched_text],
  }
}

export async function fetchGroups(signal?: AbortSignal): Promise<EntityGroup[]> {
  const response = await authFetch('/groups', { signal })
  if (!response.ok) throw await apiError(response, 'could not load groups')
  return ((await response.json()) as EntityGroupList).groups
}

export async function createGroup(name: string, entityIds: number[]): Promise<EntityGroup> {
  const response = await authFetch('/groups', jsonRequest('POST', { name, entity_ids: entityIds }))
  if (!response.ok) throw await apiError(response, 'could not save the group')
  return (await response.json()) as EntityGroup
}

export async function updateGroup(
  groupId: number,
  name: string,
  entityIds: number[],
): Promise<EntityGroup> {
  const response = await authFetch(
    `/groups/${groupId}`,
    jsonRequest('PATCH', { name, entity_ids: entityIds }),
  )
  if (!response.ok) throw await apiError(response, 'could not save the group')
  return (await response.json()) as EntityGroup
}

export async function deleteGroup(groupId: number): Promise<void> {
  const response = await authFetch(`/groups/${groupId}`, { method: 'DELETE' })
  if (!response.ok) throw await apiError(response, 'could not delete the group')
}

export async function suggestEntities(
  query: string,
  signal?: AbortSignal,
): Promise<EntitySuggestion[]> {
  const params = new URLSearchParams({ q: query })
  const response = await authFetch(`/entities/suggest?${params}`, { signal })
  if (!response.ok) throw await apiError(response, 'could not search entities')
  return ((await response.json()) as EntitySuggestions).entities
}

function jsonRequest(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

/** FastAPI errors are {"detail": ...}; fall back to the status line. */
async function apiError(response: Response, fallback: string): Promise<ApiError> {
  let detail = `${fallback} (${response.status})`
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') detail = body.detail
  } catch {
    /* non-JSON error body — keep the status line */
  }
  return new ApiError(detail, response.status)
}
