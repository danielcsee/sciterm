import { useState } from 'react'
import EntityChip from '../components/EntityChip'
import type { EntityGroup, GroupEntity } from './api'
import EntityTypeahead from './EntityTypeahead'
import SaveGroupModal from './SaveGroupModal'

interface Props {
  onSaved: (group: EntityGroup) => void
  onCancel: () => void
}

/**
 * A new group in progress: type-ahead and Save Group on one row, the chosen
 * entities as removable chips beneath. Save is disabled while there are none.
 */
export default function GroupBuilder({ onSaved, onCancel }: Props) {
  const [entities, setEntities] = useState<GroupEntity[]>([])
  const [saving, setSaving] = useState(false)
  const chosenIds = new Set(entities.map((entity) => entity.entity_id))

  return (
    <section className="group-builder" aria-label="New group">
      <div className="group-builder-row">
        <EntityTypeahead
          excludeIds={chosenIds}
          onSelect={(entity) => setEntities((prev) => [...prev, entity])}
          autoFocus
        />
        <button
          type="button"
          className="group-button group-button-primary"
          onClick={() => setSaving(true)}
          disabled={entities.length === 0}
        >
          Save Group
        </button>
        <button type="button" className="group-button" onClick={onCancel}>
          Cancel
        </button>
      </div>

      {entities.length > 0 && (
        <div className="entity-chip-list">
          {entities.map((entity) => (
            <EntityChip
              key={entity.entity_id}
              entity={entity}
              onRemove={() =>
                setEntities((prev) => prev.filter((e) => e.entity_id !== entity.entity_id))
              }
            />
          ))}
        </div>
      )}

      {saving && (
        <SaveGroupModal
          entities={entities}
          onSaved={onSaved}
          onClose={() => setSaving(false)}
        />
      )}
    </section>
  )
}
