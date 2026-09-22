import { useState } from 'react'
import { submitOnEnter, useModalDialog } from '../groups/useModalDialog'

interface Props {
  defaultName: string
  error: string | null
  saving: boolean
  onSave: (name: string) => Promise<boolean>
  onClose: () => void
}

/** Names and persists the complete conversation currently shown in chat. */
export default function SaveConversationModal({
  defaultName,
  error,
  saving,
  onSave,
  onClose,
}: Props) {
  const ref = useModalDialog(onClose)
  const [name, setName] = useState(defaultName)
  const canSave = !saving && name.trim().length > 0

  async function save() {
    if (!canSave) return
    if (await onSave(name.trim())) onClose()
  }

  return (
    <dialog className="code-dialog" ref={ref} aria-labelledby="save-conversation-title">
      <form
        className="code-form"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <h2 className="code-title" id="save-conversation-title">
          Save Conversation
        </h2>
        <p className="code-intro">Give this conversation a name so you can reopen it later.</p>

        <label className="code-label" htmlFor="save-conversation-name">
          Name
        </label>
        <input
          className="code-input"
          id="save-conversation-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => submitOnEnter(event, save)}
          maxLength={200}
          autoComplete="off"
          autoFocus
          disabled={saving}
          aria-invalid={error !== null}
          aria-describedby={error ? 'save-conversation-error' : undefined}
        />
        {error && (
          <p className="code-error" id="save-conversation-error" role="alert">
            {error}
          </p>
        )}

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
