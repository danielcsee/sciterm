import type { IntentEntity } from '../api'

interface Props {
  entities: IntentEntity[]
}

/** The candidate entities OpenAI confirmed, each with the phrase that named it. */
export default function IntentEntityList({ entities }: Props) {
  if (entities.length === 0) {
    return <p className="entity-match-empty">OpenAI resolved no entities in this query.</p>
  }

  return (
    <section className="entity-matches" aria-label="OpenAI resolved entities">
      <div className="entity-match-group">
        <ol>
          {entities.map((entity) => (
            <li key={entity.entity_id}>
              <span className="entity-match-name">{entity.name ?? entity.identifier}</span>{' '}
              <span className="entity-match-meta">
                {entity.identifier} · {entity.entity_type} · from “{entity.phrase}”
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
