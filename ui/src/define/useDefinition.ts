import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { ApiError } from '../api'
import { defineTerm, deleteAnnotation } from './api'
import type { AnnotationDraft, UserAnnotation } from './types'

/** Every entry keeps its annotation, whose selector places its underline. */
type DefinitionEntry =
  | { id: string; phrase: string; status: 'loading'; annotation: AnnotationDraft }
  | { id: string; phrase: string; status: 'done'; text: string; annotation: UserAnnotation }
  | { id: string; phrase: string; status: 'error'; error: string; annotation: AnnotationDraft }

/** A hidden definition keeps its card title but loses its text and underline. */
export type Definition = DefinitionEntry & { hidden: boolean }

/** Shown for a saved annotation whose definition never arrived. */
const UNFINISHED_DEFINITION = 'The definition did not finish. Highlight it again to retry.'

export interface DefinitionState {
  /** Every definition, each flagged hidden or shown; hiding lasts until a reload. */
  definitions: Definition[]
  request: (annotation: AnnotationDraft) => void
  hydrate: (annotations: UserAnnotation[]) => void
  clear: () => void
  /** Hide or show again, for this session only; the saved annotation is untouched. */
  toggleHidden: (id: string) => void
  /** Delete the saved annotation, then drop it. Rejects if the server refused. */
  remove: (id: string) => Promise<void>
}

/** Definitions shown newest first in the sidebar. */
export function useDefinition(): DefinitionState {
  const [allDefinitions, setDefinitions] = useState<DefinitionEntry[]>([])
  // Kept across hydrates, so reopening the same paper does not bring them back.
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set())
  const controllersRef = useRef(new Set<AbortController>())
  const definitions = useMemo(
    () => allDefinitions.map((definition) => ({ ...definition, hidden: hidden.has(definition.id) })),
    [allDefinitions, hidden],
  )

  const clear = useCallback(() => {
    abortAll(controllersRef.current)
    setDefinitions([])
  }, [])

  const request = useCallback((annotation: AnnotationDraft) => {
    const controller = new AbortController()
    controllersRef.current.add(controller)
    setDefinitions((current) => [
      { id: annotation.id, phrase: annotation.phrase, status: 'loading', annotation },
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
    setDefinitions(annotations.map(savedDefinition))
  }, [])

  const toggleHidden = useCallback((id: string) => {
    setHidden((current) => toggled(current, id))
  }, [])

  const remove = useCallback(async (id: string) => {
    await deleteAnnotation(id)
    setDefinitions((current) => current.filter((definition) => definition.id !== id))
  }, [])

  useEffect(() => {
    const controllers = controllersRef.current
    return () => abortAll(controllers)
  }, [])

  return { definitions, request, hydrate, clear, toggleHidden, remove }
}

function toggled(set: ReadonlySet<string>, id: string): ReadonlySet<string> {
  const copy = new Set(set)
  if (!copy.delete(id)) copy.add(id)
  return copy
}

function savedDefinition(annotation: UserAnnotation): DefinitionEntry {
  const common = { id: annotation.id, phrase: annotation.phrase, annotation }
  return annotation.definition === null
    ? { ...common, status: 'error', error: UNFINISHED_DEFINITION }
    : { ...common, status: 'done', text: annotation.definition }
}

async function fetchDefinition(
  annotation: AnnotationDraft,
  controller: AbortController,
  controllers: Set<AbortController>,
  setDefinitions: Dispatch<SetStateAction<DefinitionEntry[]>>,
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
      annotation,
    })
  } finally {
    controllers.delete(controller)
  }
}

function replaceDefinition(
  setDefinitions: Dispatch<SetStateAction<DefinitionEntry[]>>,
  replacement: DefinitionEntry,
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
