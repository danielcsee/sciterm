import { useEffect, useState } from 'react'
import { ApiError } from '../api'
import { MIN_TYPEAHEAD_LENGTH, suggestEntities, type EntitySuggestion } from './api'

/** Quiet time after the last keystroke before searching. */
export const TYPEAHEAD_DEBOUNCE_MS = 250

interface SuggestionState {
  /** The input these results answer, so stale ones are never shown. */
  query: string
  suggestions: EntitySuggestion[]
  error: string | null
}

const EMPTY: SuggestionState = { query: '', suggestions: [], error: null }

export interface EntitySuggestionsResult {
  suggestions: EntitySuggestion[]
  loading: boolean
  error: string | null
  /** True once the trimmed input is long enough to search. */
  searchable: boolean
}

/**
 * Debounced entity suggestions for a type-ahead input.
 *
 * Each new input cancels the pending timer and aborts the request in flight,
 * so a slow answer to "oste" can never overwrite the answer to "osteop".
 */
export function useEntitySuggestions(input: string): EntitySuggestionsResult {
  const query = input.trim()
  const searchable = query.length >= MIN_TYPEAHEAD_LENGTH
  const [state, setState] = useState<SuggestionState>(EMPTY)

  useEffect(() => {
    if (!searchable) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void loadSuggestions(query, controller.signal, setState)
    }, TYPEAHEAD_DEBOUNCE_MS)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, searchable])

  // While the next answer loads, the last one stays up: blanking the list on
  // every keystroke makes it flicker.
  const current = searchable && state.query === query
  return {
    suggestions: searchable ? state.suggestions : [],
    loading: searchable && !current,
    error: current ? state.error : null,
    searchable,
  }
}

async function loadSuggestions(
  query: string,
  signal: AbortSignal,
  setState: (state: SuggestionState) => void,
): Promise<void> {
  try {
    const suggestions = await suggestEntities(query, signal)
    setState({ query, suggestions, error: null })
  } catch (err) {
    if (signal.aborted) return
    const error = err instanceof ApiError ? err.message : 'Could not reach the server.'
    setState({ query, suggestions: [], error })
  }
}
