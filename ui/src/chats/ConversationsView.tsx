import type { SavedChatSummary } from './api'
import ConversationTile from './ConversationTile'

interface Props {
  conversations: SavedChatSummary[]
  loading: boolean
  opening: boolean
  error: string | null
  onClose: () => void
  onOpen: (conversationId: number) => void
}

/** Lists every saved conversation using the same tile layout as Smart Groups. */
export default function ConversationsView({
  conversations,
  loading,
  opening,
  error,
  onClose,
  onOpen,
}: Props) {
  return (
    <section className="conversations" aria-label="Conversations">
      <header className="groups-header">
        <div>
          <h1 className="corpus-title">Conversations</h1>
          {conversations.length > 0 && (
            <p className="corpus-count">
              {conversations.length} conversation{conversations.length === 1 ? '' : 's'}
            </p>
          )}
        </div>
        <button className="corpus-close" type="button" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>

      <div className="conversations-scroll">
        {error ? (
          <p className="results-message results-error" role="alert">{error}</p>
        ) : loading ? (
          <p className="results-message">Loading…</p>
        ) : conversations.length === 0 ? (
          <p className="results-message">
            No conversations yet. Save one from the chat to see it here.
          </p>
        ) : (
          <div className="group-grid">
            {conversations.map((conversation) => (
              <ConversationTile
                key={conversation.chat_id}
                conversation={conversation}
                disabled={opening}
                onOpen={() => onOpen(conversation.chat_id)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
