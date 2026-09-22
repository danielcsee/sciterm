import { useState } from 'react'
import { useModalDialog } from '../groups/useModalDialog'

interface Props {
  title: string
  /** Resolves once the chat is gone; a rejection's message is shown here. */
  onConfirm: () => Promise<void>
  onClose: () => void
}

/** "Are you sure?" before a chat is permanently deleted. */
export default function DeleteChatModal({ title, onConfirm, onClose }: Props) {
  const ref = useModalDialog(onClose)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function confirm() {
    setDeleting(true)
    setError(null)
    try {
      await onConfirm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete that chat.')
      setDeleting(false)
    }
  }

  return (
    <dialog className="code-dialog" ref={ref} aria-labelledby="delete-chat-title">
      <div className="code-form">
        <h2 className="code-title" id="delete-chat-title">
          Delete this conversation?
        </h2>
        <p className="code-intro">
          “{title}” and its annotations will be permanently deleted. This cannot be undone.
        </p>
        {error && (
          <p className="code-error" role="alert">
            {error}
          </p>
        )}
        <div className="code-actions">
          <button className="code-cancel" type="button" onClick={onClose} disabled={deleting}>
            No
          </button>
          <button
            className="code-submit code-danger"
            type="button"
            onClick={() => void confirm()}
            disabled={deleting}
          >
            {deleting ? 'Deleting…' : 'Yes, delete'}
          </button>
        </div>
      </div>
    </dialog>
  )
}
