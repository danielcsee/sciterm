import { useEffect, useRef } from 'react'
import type { Definition } from './useDefinition'

interface Props {
  definitions: Definition[]
  onClose: () => void
}

/** Highlighted phrases and their definitions, newest first. */
export default function DefinitionPanel({ definitions, onClose }: Props) {
  const scrollRef = useRef<HTMLElement>(null)
  const newestId = definitions[0]?.id

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
  }, [newestId])

  return (
    <section className="definitions" aria-live="polite" aria-label="Definitions" ref={scrollRef}>
      {definitions.map((definition, index) => (
        <article className="definition" key={definition.id}>
          <div className="definition-head">
            <h2 className="definition-phrase">{definition.phrase}</h2>
            {index === 0 && (
              <button
                type="button"
                className="refs-close"
                onClick={onClose}
                aria-label="Close definitions"
                title="Close"
              >
                ✕
              </button>
            )}
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
        </article>
      ))}
    </section>
  )
}
