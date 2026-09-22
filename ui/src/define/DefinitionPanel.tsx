import type { Definition } from './useDefinition'

interface Props {
  definition: Definition
  onClose: () => void
}

/** The highlighted phrase and its definition, in the sidebar's results slot. */
export default function DefinitionPanel({ definition, onClose }: Props) {
  return (
    <section className="definition" aria-live="polite" aria-label="Definition">
      <div className="definition-head">
        <h2 className="definition-phrase">{definition.phrase}</h2>
        <button
          type="button"
          className="refs-close"
          onClick={onClose}
          aria-label="Close definition"
          title="Close"
        >
          ✕
        </button>
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
    </section>
  )
}
