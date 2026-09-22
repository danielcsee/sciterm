import { useEffect, useRef, useState } from 'react'
import TrashIcon from '../components/TrashIcon'
import type { Definition } from './useDefinition'

type DeleteStatus = 'deleting' | { error: string }

interface Props {
  definitions: Definition[]
  onHide: (id: string) => void
  /** Resolves once the annotation is deleted; rejects if the server refused. */
  onDelete: (id: string) => Promise<void>
}

/** Highlighted phrases and their definitions, newest first. */
export default function DefinitionPanel({ definitions, onHide, onDelete }: Props) {
  const scrollRef = useRef<HTMLElement>(null)
  const newestId = definitions[0]?.id
  // Keyed by definition id: in flight, or the server's refusal to show.
  const [deletes, setDeletes] = useState<ReadonlyMap<string, DeleteStatus>>(new Map())

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
  }, [newestId])

  async function remove(id: string) {
    setDeletes((current) => new Map(current).set(id, 'deleting'))
    try {
      await onDelete(id)
      setDeletes((current) => withoutKey(current, id))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not delete that annotation.'
      setDeletes((current) => new Map(current).set(id, { error: message }))
    }
  }

  return (
    <section className="definitions" aria-live="polite" aria-label="Definitions" ref={scrollRef}>
      {definitions.map((definition) => (
        <article className="definition" key={definition.id}>
          <div className="definition-head">
            <h2 className="definition-phrase">{definition.phrase}</h2>
            <DefinitionActions
              phrase={definition.phrase}
              // A definition still being generated is written to once more
              // when it arrives, so it cannot be deleted from under that.
              canDelete={definition.status !== 'loading' && deletes.get(definition.id) !== 'deleting'}
              onHide={() => onHide(definition.id)}
              onDelete={() => void remove(definition.id)}
            />
          </div>
          {definition.status === 'loading' && (
            <div className="results-loading" role="status">
              <span className="spinner" aria-hidden="true" />
              <span>Defining…</span>
            </div>
          )}
          {definition.status === 'done' && <p className="definition-text">{definition.text}</p>}
          {definition.status === 'error' && (
            <p className="results-message results-error">{definition.error}</p>
          )}
          <DeleteError status={deletes.get(definition.id)} />
        </article>
      ))}
    </section>
  )
}

function DefinitionActions({
  phrase,
  canDelete,
  onHide,
  onDelete,
}: {
  phrase: string
  canDelete: boolean
  onHide: () => void
  onDelete: () => void
}) {
  return (
    <div className="definition-actions">
      <button
        type="button"
        className="definition-hide"
        onClick={onHide}
        aria-label={`Hide ${phrase}`}
        title="Hide until reload; it stays saved"
      >
        Hide
      </button>
      <button
        type="button"
        className="icon-delete"
        onClick={onDelete}
        disabled={!canDelete}
        aria-label={`Delete ${phrase}`}
        title="Delete permanently"
      >
        <TrashIcon />
      </button>
    </div>
  )
}

function DeleteError({ status }: { status: DeleteStatus | undefined }) {
  if (status === undefined || status === 'deleting') return null
  return (
    <p className="results-message results-error" role="alert">
      {status.error}
    </p>
  )
}

function withoutKey<V>(map: ReadonlyMap<string, V>, key: string): ReadonlyMap<string, V> {
  const copy = new Map(map)
  copy.delete(key)
  return copy
}
