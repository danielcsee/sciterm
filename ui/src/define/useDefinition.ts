import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api'
import { defineTerm } from './api'

export type Definition =
  | { phrase: string; status: 'loading' }
  | { phrase: string; status: 'done'; text: string }
  | { phrase: string; status: 'error'; error: string }

export interface DefinitionState {
  definition: Definition | null
  request: (phrase: string, surroundingContext: string | null) => void
  clear: () => void
}

/** The one definition the sidebar shows. A new request supersedes the last. */
export function useDefinition(): DefinitionState {
  const [definition, setDefinition] = useState<Definition | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const clear = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setDefinition(null)
  }, [])

  const request = useCallback((phrase: string, surroundingContext: string | null) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setDefinition({ phrase, status: 'loading' })
    void fetchDefinition(phrase, surroundingContext, controller.signal, setDefinition)
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  return { definition, request, clear }
}

async function fetchDefinition(
  phrase: string,
  surroundingContext: string | null,
  signal: AbortSignal,
  setDefinition: (definition: Definition) => void,
): Promise<void> {
  try {
    const response = await defineTerm({ phrase, surrounding_context: surroundingContext }, signal)
    setDefinition({ phrase, status: 'done', text: response.definition })
  } catch (err) {
    if (signal.aborted) return
    const error = err instanceof ApiError ? err.message : 'Could not reach the definition service.'
    setDefinition({ phrase, status: 'error', error })
  }
}
