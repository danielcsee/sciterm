import { entityLabel, type EntityLabelSource } from '../api'

interface Props {
  entity: EntityLabelSource
  /** Present when the chip can be removed; draws the 'x'. */
  onRemove?: () => void
}

/**
 * An entity as a static oval — `PaperEntities`' pill, minus the selecting.
 *
 * It shares the pill's shape and colours (`.entity-pill, .entity-chip` in the
 * stylesheet). The difference is behaviour: a pill is itself a button, while a
 * chip is inert and only its 'x' is interactive, so the hover affordance sits
 * on the 'x' alone.
 */
export default function EntityChip({ entity, onRemove }: Props) {
  const label = entityLabel(entity)
  return (
    <span className={`entity-chip${onRemove ? ' entity-chip-removable' : ''}`} title={label}>
      <span className="entity-chip-label">{label}</span>
      {onRemove && (
        <button
          type="button"
          className="entity-chip-remove"
          aria-label={`Remove ${label}`}
          onClick={onRemove}
        >
          ×
        </button>
      )}
    </span>
  )
}
