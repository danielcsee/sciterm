import OutgoingArrowIcon from '../components/OutgoingArrowIcon'
import type { SavedChatSummary } from './api'

interface Props {
  conversation: SavedChatSummary
  disabled: boolean
  onOpen: () => void
}

/** A saved conversation preview; opening restores it in the main chat pane. */
export default function ConversationTile({ conversation, disabled, onOpen }: Props) {
  return (
    <button
      type="button"
      className="conversation-tile"
      onClick={onOpen}
      disabled={disabled}
      aria-label={`Open conversation ${conversation.title}`}
    >
      <span className="conversation-tile-name">{conversation.title}</span>
      <span className="conversation-tile-open">
        Open conversation
        <OutgoingArrowIcon />
      </span>
    </button>
  )
}
