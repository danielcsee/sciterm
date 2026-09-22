/** Typed access to POST /define. Mirrors api/define_term/models.py. */

import { ApiError } from '../api'
import { authFetch } from '../auth'

export interface DefineTermRequest {
  phrase: string
  /** The paragraph the phrase was in; null for highlights over 12 words. */
  surrounding_context: string | null
}

export interface DefineTermResponse {
  definition: string
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
