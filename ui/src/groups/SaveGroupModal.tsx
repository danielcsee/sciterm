import { useState } from 'react'
import { ApiError } from '../api'
import EntityChip from '../components/EntityChip'
import { createGroup, type EntityGroup, type GroupEntity } from './api'
import { submitOnEnter, useModalDialog } from './useModalDialog'

interface Props {
  entities: GroupEntity[]
  onSaved: (group: EntityGroup) => void
  onClose: () => void
}

/** Name a new group and save it. A taken name is reported under the field. */
export default function SaveGroupModal({ entities, onSaved, onClose }: Props) {
  const ref = useModalDialog(onClose)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const canSave = !saving && name.trim().length > 0 && entities.length > 0

  async function save() {
    if (!canSave) return
    setSaving(true)
    setError(null)
    try {
      onSaved(await createGroup(name.trim(), entities.map((entity) => entity.entity_id)))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
      setSaving(false)
    }
  }

  return (
    <dialog className="code-dialog group-dialog" ref={ref} aria-labelledby="save-group-title">
      <form
        className="code-form"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <h2 className="code-title" id="save-group-title">
          Save group
        </h2>

        <label className="code-label" htmlFor="save-group-name">
          Name
        </label>
        <input
          className="code-input"
          id="save-group-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => submitOnEnter(event, save)}
          maxLength={100}
          autoComplete="off"
          autoFocus
          disabled={saving}
          aria-invalid={error !== null}
          aria-describedby={error ? 'save-group-error' : undefined}
        />
        {error && (
          <p className="code-error" id="save-group-error" role="alert">
            {error}
          </p>
        )}

        <p className="code-label code-label-spaced">
          {entities.length} entit{entities.length === 1 ? 'y' : 'ies'}
        </p>
        <div className="entity-chip-list">
          {entities.map((entity) => (
            <EntityChip key={entity.entity_id} entity={entity} />
          ))}
        </div>

        <div className="code-actions">
          <button className="code-cancel" type="button" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="code-submit" type="submit" disabled={!canSave}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
