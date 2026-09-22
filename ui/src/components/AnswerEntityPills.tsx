import type { AnswerEntity } from '../api'

interface Props {
  entities: AnswerEntity[]
  selectedIds: ReadonlySet<number>
  /** Called with an entity on hover or focus, and with null when it ends. */
  onActivate: (entityId: number | null) => void
  onToggle: (entityId: number) => void
}

/**
 * The entities an answer names, one selectable pill each, beneath the answer.
 * Hovering or focusing a pill underlines every phrase naming that entity.
 */
export default function AnswerEntityPills({
  entities,
  selectedIds,
  onActivate,
  onToggle,
}: Props) {
  if (entities.length === 0) return null
  return (
    <ul className="answer-entity-pills" aria-label="Entities named in this answer">
      {entities.map((entity) => {
        const selected = selectedIds.has(entity.entity_id)
        return (
          <li key={entity.entity_id}>
            <button
              type="button"
              className={`entity-pill answer-entity-pill${
                selected ? ' entity-pill-selected' : ''
              }`}
              aria-pressed={selected}
              title={`${entity.identifier} · ${entity.entity_type}`}
              onClick={() => onToggle(entity.entity_id)}
              onMouseEnter={() => onActivate(entity.entity_id)}
              onMouseLeave={() => onActivate(null)}
              onFocus={() => onActivate(entity.entity_id)}
              onBlur={() => onActivate(null)}
            >
              {entity.name ?? entity.identifier}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
