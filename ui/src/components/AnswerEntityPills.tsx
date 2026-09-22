import type { AnswerEntity } from '../api'

interface Props {
  entities: AnswerEntity[]
  /** Called with an entity on hover or focus, and with null when it ends. */
  onActivate: (entityId: number | null) => void
}

/**
 * The entities an answer names, one pill each, beneath the answer. Hovering or
 * focusing a pill underlines every phrase naming that entity in the answer.
 */
export default function AnswerEntityPills({ entities, onActivate }: Props) {
  if (entities.length === 0) return null
  return (
    <ul className="answer-entity-pills" aria-label="Entities named in this answer">
      {entities.map((entity) => (
        <li key={entity.entity_id}>
          <span
            className="entity-pill answer-entity-pill"
            tabIndex={0}
            title={`${entity.identifier} · ${entity.entity_type}`}
            onMouseEnter={() => onActivate(entity.entity_id)}
            onMouseLeave={() => onActivate(null)}
            onFocus={() => onActivate(entity.entity_id)}
            onBlur={() => onActivate(null)}
          >
            {entity.name ?? entity.identifier}
          </span>
        </li>
      ))}
    </ul>
  )
}
