import OutgoingArrowIcon from '../components/OutgoingArrowIcon'
import TrashIcon from '../components/TrashIcon'
import type { SavedChatSummary } from './api'

interface Props {
  conversation: SavedChatSummary
  disabled: boolean
  onOpen: () => void
  onDelete: () => void
}

/**
 * A saved conversation preview; opening restores it in the main chat pane.
 * The open button covers the tile, and the delete button sits over its corner:
 * a button cannot be nested inside another.
 */
export default function ConversationTile({ conversation, disabled, onOpen, onDelete }: Props) {
  return (
    <div className={`conversation-tile${disabled ? ' conversation-tile-disabled' : ''}`}>
      <button
        type="button"
        className="conversation-tile-body"
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
      <button
        type="button"
        className="icon-delete conversation-tile-delete"
        onClick={onDelete}
        disabled={disabled}
        aria-label={`Delete conversation ${conversation.title}`}
        title="Delete conversation"
      >
        <TrashIcon />
      </button>
    </div>
  )
}
