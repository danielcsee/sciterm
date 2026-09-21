import { useState } from 'react'
import { ApiError } from '../api'
import { deleteGroup, updateGroup, type EntityGroup, type GroupEntity } from './api'
import EntityChip from '../components/EntityChip'
import EntityTypeahead from './EntityTypeahead'
import { submitOnEnter, useModalDialog } from './useModalDialog'

interface Props {
  group: EntityGroup
  onSaved: (group: EntityGroup) => void
  onDeleted: (groupId: number) => void
  onClose: () => void
}

/**
 * Rename a group, add or remove its entities, or delete it.
 *
 * Nothing is written until Save; Cancel and Escape discard the edits. Delete
 * asks once more in place — the button turns into a confirmation — rather than
 * through `window.confirm`, which would block the whole page.
 */
export default function EditGroupModal({ group, onSaved, onDeleted, onClose }: Props) {
  const ref = useModalDialog(onClose)
  const [name, setName] = useState(group.name)
  const [entities, setEntities] = useState<GroupEntity[]>(group.entities)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const chosenIds = new Set(entities.map((entity) => entity.entity_id))
  const canSave = !busy && name.trim().length > 0 && entities.length > 0

  async function save() {
    if (!canSave) return
    await run(async () =>
      onSaved(await updateGroup(group.group_id, name.trim(), [...chosenIds])),
    )
  }

  async function remove() {
    await run(async () => {
      await deleteGroup(group.group_id)
      onDeleted(group.group_id)
    })
  }

  /** One busy/error path for both writes, so they can never disagree. */
  async function run(write: () => Promise<void>) {
    setBusy(true)
    setError(null)
    try {
      await write()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
      setBusy(false)
    }
  }

  return (
    <dialog className="code-dialog group-dialog" ref={ref} aria-labelledby="edit-group-title">
      <form
        className="code-form"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <h2 className="code-title" id="edit-group-title">
          Edit group
        </h2>

        <label className="code-label" htmlFor="edit-group-name">
          Name
        </label>
        <input
          className="code-input"
          id="edit-group-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => submitOnEnter(event, save)}
          maxLength={100}
          autoComplete="off"
          disabled={busy}
          aria-invalid={error !== null}
          aria-describedby={error ? 'edit-group-error' : undefined}
        />
        {error && (
          <p className="code-error" id="edit-group-error" role="alert">
            {error}
          </p>
        )}

        <p className="code-label code-label-spaced">Entities</p>
        <EntityTypeahead
          excludeIds={chosenIds}
          onSelect={(entity) => setEntities((prev) => [...prev, entity])}
          placeholder="Add an entity…"
        />
        <div className="entity-chip-list group-dialog-chips">
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
        {entities.length === 0 && (
          <p className="group-hint">A group needs at least one entity.</p>
        )}

        <div className="code-actions">
          <DeleteButton
            confirming={confirmingDelete}
            disabled={busy}
            onAsk={() => setConfirmingDelete(true)}
            onConfirm={() => void remove()}
          />
          <button className="code-cancel" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="code-submit" type="submit" disabled={!canSave}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </dialog>
  )
}

function DeleteButton({
  confirming,
  disabled,
  onAsk,
  onConfirm,
}: {
  confirming: boolean
  disabled: boolean
  onAsk: () => void
  onConfirm: () => void
}) {
  return (
    <button
      className={`group-delete${confirming ? ' group-delete-confirm' : ''}`}
      type="button"
      onClick={confirming ? onConfirm : onAsk}
      disabled={disabled}
    >
      {confirming ? 'Click again to delete' : 'Delete'}
    </button>
  )
}
