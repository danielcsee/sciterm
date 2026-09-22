import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { ApiError } from '../api'
import { defineTerm } from './api'
import type { AnnotationDraft, UserAnnotation } from './types'

export type Definition =
  | { id: string; phrase: string; status: 'loading' }
  | { id: string; phrase: string; status: 'done'; text: string; annotation: UserAnnotation }
  | { id: string; phrase: string; status: 'error'; error: string }

export interface DefinitionState {
  definitions: Definition[]
  request: (annotation: AnnotationDraft) => void
  hydrate: (annotations: UserAnnotation[]) => void
  clear: () => void
}

/** Definitions shown newest first in the sidebar. */
export function useDefinition(): DefinitionState {
  const [definitions, setDefinitions] = useState<Definition[]>([])
  const controllersRef = useRef(new Set<AbortController>())

  const clear = useCallback(() => {
    abortAll(controllersRef.current)
    setDefinitions([])
  }, [])

  const request = useCallback((annotation: AnnotationDraft) => {
    const controller = new AbortController()
    controllersRef.current.add(controller)
    setDefinitions((current) => [
      { id: annotation.id, phrase: annotation.phrase, status: 'loading' },
      ...current,
    ])
    void fetchDefinition(
      annotation,
      controller,
      controllersRef.current,
      setDefinitions,
    )
  }, [])

  const hydrate = useCallback((annotations: UserAnnotation[]) => {
    setDefinitions(
      annotations.map((annotation) => ({
        id: annotation.id,
        phrase: annotation.phrase,
        status: 'done' as const,
        text: annotation.definition,
        annotation,
      })),
    )
  }, [])

  useEffect(() => {
    const controllers = controllersRef.current
    return () => abortAll(controllers)
  }, [])

  return { definitions, request, hydrate, clear }
}

async function fetchDefinition(
  annotation: AnnotationDraft,
  controller: AbortController,
  controllers: Set<AbortController>,
  setDefinitions: Dispatch<SetStateAction<Definition[]>>,
): Promise<void> {
  try {
    const response = await defineTerm(
      {
        phrase: annotation.phrase,
        surrounding_context: annotation.surrounding_context,
        annotation,
      },
      controller.signal,
    )
    replaceDefinition(setDefinitions, {
      id: annotation.id,
      phrase: annotation.phrase,
      status: 'done',
      text: response.definition,
      annotation: response.annotation,
    })
  } catch (err) {
    if (controller.signal.aborted) return
    const error = err instanceof ApiError ? err.message : 'Could not reach the definition service.'
    replaceDefinition(setDefinitions, {
      id: annotation.id,
      phrase: annotation.phrase,
      status: 'error',
      error,
    })
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
