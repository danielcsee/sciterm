import type { SavedChatSummary } from './api'

interface Props {
  chats: SavedChatSummary[]
  activeChatId: number | null
  canSave: boolean
  busy: boolean
  error: string | null
  onLoad: (chatId: number) => void
  onSave: () => void
}

export default function SavedChatControls({
  chats,
  activeChatId,
  canSave,
  busy,
  error,
  onLoad,
  onSave,
}: Props) {
  return (
    <div className="saved-chat-bar" aria-label="Saved chats">
      <select
        className="saved-chat-select"
        aria-label="Load a saved chat"
        value={activeChatId ?? ''}
        disabled={busy}
        onChange={(event) => {
          const id = Number(event.target.value)
          if (id > 0) onLoad(id)
        }}
      >
        <option value="">Saved chats…</option>
        {chats.map((chat) => (
          <option key={chat.chat_id} value={chat.chat_id}>
            {chat.title}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="saved-chat-save"
        disabled={!canSave || busy}
        onClick={onSave}
      >
        {busy ? 'Saving…' : activeChatId === null ? 'Save chat' : 'Update saved chat'}
      </button>
      {error && <span className="saved-chat-error" role="alert">{error}</span>}
    </div>
  )
}
