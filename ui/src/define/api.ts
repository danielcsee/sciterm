/** Typed access to POST /define. Mirrors api/define_term/models.py. */

import { ApiError } from '../api'
import { authFetch } from '../auth'
import type { AnnotationDraft, UserAnnotation } from './types'

export interface DefineTermRequest {
  phrase: string
  /** The paragraph the phrase was in; null for highlights over 12 words. */
  surrounding_context: string | null
  annotation: AnnotationDraft
}

export interface DefineTermResponse {
  definition: string
  annotation: UserAnnotation
}

export async function defineTerm(
  request: DefineTermRequest,
  signal?: AbortSignal,
): Promise<DefineTermResponse> {
  const response = await authFetch('/define', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    let detail = `could not define that (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body — keep the status line */
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as DefineTermResponse
}

export async function listAnnotations(
  source: { chatId: number } | { paperId: number },
  signal?: AbortSignal,
): Promise<UserAnnotation[]> {
  const params = new URLSearchParams(
    'chatId' in source
      ? { chat_id: String(source.chatId) }
      : { paper_id: String(source.paperId) },
  )
  const response = await authFetch(`/annotations?${params}`, { signal })
  if (!response.ok) throw new ApiError('Could not load annotations.', response.status)
  const body = (await response.json()) as { annotations: UserAnnotation[] }
  return body.annotations
}

/** Permanently removes one of the caller's annotations. */
export async function deleteAnnotation(annotationId: string): Promise<void> {
  const response = await authFetch(`/annotations/${encodeURIComponent(annotationId)}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new ApiError('Could not delete that annotation.', response.status)
}
