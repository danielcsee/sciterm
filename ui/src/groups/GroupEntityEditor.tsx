import { useState, type ReactNode } from 'react'
import EntityChip from '../components/EntityChip'
import type { GroupEntity } from './api'
import EntityTypeahead from './EntityTypeahead'

interface Props {
  /** Used for the list's accessible name. */
  groupName: string
  /** Shown first on the chips' row: the results count. */
  summary: ReactNode
  entities: GroupEntity[]
  onRemove: (entityId: number) => void
  onAdd: (entity: GroupEntity) => void
}

/**
 * The entities a results page searches for, as removable chips, with
 * "+ Add Entities" beneath opening the same type-ahead as New Group.
 *
 * A picked entity joins the end of the row and flashes orange, then fades to
 * a normal chip. The flash is a CSS animation on mount, so it plays once per
 * add — including when an entity removed earlier is added back.
 */
export default function GroupEntityEditor({
  groupName,
  summary,
  entities,
  onRemove,
  onAdd,
}: Props) {
  const [adding, setAdding] = useState(false)
  const [addedId, setAddedId] = useState<number | null>(null)
  const chosenIds = new Set(entities.map((entity) => entity.entity_id))

  function add(entity: GroupEntity) {
    setAddedId(entity.entity_id)
    onAdd(entity)
  }

  return (
    <div className="group-results-editor">
      <div className="group-results-meta">
        {summary}
        <ul className="group-results-entities" aria-label={`Entities in ${groupName}`}>
          {entities.map((entity) => (
            <li
              key={entity.entity_id}
              className={entity.entity_id === addedId ? 'group-results-chip-added' : undefined}
            >
              <EntityChip entity={entity} onRemove={() => onRemove(entity.entity_id)} />
            </li>
          ))}
        </ul>
      </div>

      {adding ? (
        <div className="group-results-add-row">
          <EntityTypeahead excludeIds={chosenIds} onSelect={add} autoFocus />
          <button type="button" className="group-button" onClick={() => setAdding(false)}>
            Done
          </button>
        </div>
      ) : (
        <button type="button" className="group-results-add" onClick={() => setAdding(true)}>
          <span aria-hidden="true">+</span> Add Entities
        </button>
      )}
    </div>
  )
}
