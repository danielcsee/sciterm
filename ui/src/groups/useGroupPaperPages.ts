import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api'
import { fetchEntityPapers, type PaperSubgroup, type SortOrder } from './api'

export interface GroupPaperPages {
  subgroups: PaperSubgroup[]
  page: number
  totalPages: number
  totalPapers: number
  totalSubgroups: number
  loading: boolean
  error: string | null
  /** Fetches the next page; a no-op while loading or once exhausted. */
  loadNext: () => void
}

/**
 * Pages of subgroups for papers mentioning any of `entityIds`, appended as the
 * reader scrolls. Changing `order` or the entities starts over from page 1:
 * the server sorts, so earlier pages no longer fit. No entities, no request.
 */
export function useGroupPaperPages(
  entityIds: readonly number[],
  order: SortOrder,
): GroupPaperPages {
  // A string, so a new array holding the same ids does not refetch.
  const idsKey = entityIds.join(',')
  const [subgroups, setSubgroups] = useState<PaperSubgroup[]>([])
  const [page, setPage] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [totalPapers, setTotalPapers] = useState(0)
  const [totalSubgroups, setTotalSubgroups] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const loadPage = useCallback(
    async (nextPage: number) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const ids = parseIds(idsKey)
      if (ids.length === 0) {
        // Back to "nothing loaded": page 0 hides the count and the empty message.
        setSubgroups([])
        setPage(0)
        setTotalPages(0)
        setTotalPapers(0)
        setTotalSubgroups(0)
        setError(null)
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)
      try {
        const response = await fetchEntityPapers(ids, order, nextPage, controller.signal)
        setPage(response.page)
        setTotalPages(response.total_pages)
        setTotalPapers(response.total_papers)
        setTotalSubgroups(response.total_subgroups)
        setSubgroups((prev) =>
          nextPage === 1 ? response.subgroups : appendSubgroups(prev, response.subgroups),
        )
      } catch (err) {
        if ((err as Error)?.name === 'AbortError') return
        setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
        if (nextPage === 1) setSubgroups([])
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    },
    [idsKey, order],
  )

  useEffect(() => {
    void loadPage(1)
    return () => abortRef.current?.abort()
  }, [loadPage])

  // Read inside `loadNext`, which callers hold across renders.
  const stateRef = useRef({ page, totalPages, loading })
  stateRef.current = { page, totalPages, loading }

  const loadNext = useCallback(() => {
    const { page: p, totalPages: tp, loading: busy } = stateRef.current
    if (busy || p === 0 || p >= tp) return
    void loadPage(p + 1)
  }, [loadPage])

  return { subgroups, page, totalPages, totalPapers, totalSubgroups, loading, error, loadNext }
}

/**
 * Subgroups are recomputed per request, so a paper ingested mid-scroll can
 * reshuffle them and a paper already shown can arrive again. Drop repeats:
 * React keys must hold, and a paper belongs on screen once.
 */
function appendSubgroups(prev: PaperSubgroup[], next: PaperSubgroup[]): PaperSubgroup[] {
  const seen = new Set(prev.flatMap((group) => group.papers.map((paper) => paper.paper_id)))
  const fresh = next
    .map((group) => ({ ...group, papers: group.papers.filter((p) => !seen.has(p.paper_id)) }))
    .filter((group) => group.papers.length > 0)
  return [...prev, ...fresh]
}

function parseIds(key: string): number[] {
  return key === '' ? [] : key.split(',').map(Number)
}
