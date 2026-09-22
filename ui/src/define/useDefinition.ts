import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { ApiError } from '../api'
import { defineTerm } from './api'

export type Definition =
  | { id: number; phrase: string; status: 'loading' }
  | { id: number; phrase: string; status: 'done'; text: string }
  | { id: number; phrase: string; status: 'error'; error: string }

export interface DefinitionState {
  definitions: Definition[]
  request: (phrase: string, surroundingContext: string | null) => void
  clear: () => void
}

/** Definitions shown newest first in the sidebar. */
export function useDefinition(): DefinitionState {
  const [definitions, setDefinitions] = useState<Definition[]>([])
  const controllersRef = useRef(new Set<AbortController>())
  const nextIdRef = useRef(0)

  const clear = useCallback(() => {
    abortAll(controllersRef.current)
    setDefinitions([])
  }, [])

  const request = useCallback((phrase: string, surroundingContext: string | null) => {
    const id = ++nextIdRef.current
    const controller = new AbortController()
    controllersRef.current.add(controller)
    setDefinitions((current) => [{ id, phrase, status: 'loading' }, ...current])
    void fetchDefinition(
      id,
      phrase,
      surroundingContext,
      controller,
      controllersRef.current,
      setDefinitions,
    )
  }, [])

  useEffect(() => {
    const controllers = controllersRef.current
    return () => abortAll(controllers)
  }, [])

  return { definitions, request, clear }
}

async function fetchDefinition(
  id: number,
  phrase: string,
  surroundingContext: string | null,
  controller: AbortController,
  controllers: Set<AbortController>,
  setDefinitions: Dispatch<SetStateAction<Definition[]>>,
): Promise<void> {
  try {
    const response = await defineTerm(
      { phrase, surrounding_context: surroundingContext },
      controller.signal,
    )
    replaceDefinition(setDefinitions, { id, phrase, status: 'done', text: response.definition })
  } catch (err) {
    if (controller.signal.aborted) return
    const error = err instanceof ApiError ? err.message : 'Could not reach the definition service.'
    replaceDefinition(setDefinitions, { id, phrase, status: 'error', error })
  } finally {
    controllers.delete(controller)
  }
}

function replaceDefinition(
  setDefinitions: Dispatch<SetStateAction<Definition[]>>,
  replacement: Definition,
): void {
  setDefinitions((current) =>
    current.map((definition) =>
      definition.id === replacement.id ? replacement : definition,
    ),
  )
}

function abortAll(controllers: Set<AbortController>): void {
  controllers.forEach((controller) => controller.abort())
  controllers.clear()
}
