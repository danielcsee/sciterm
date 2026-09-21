import { useState, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

/**
 * Inline disclosure that keeps debug output out of the way until asked for.
 * State is local so toggling never touches the message list — the chat's
 * auto-scroll watches `messages`, and a plain button scrolls nothing.
 */
export default function DebugDisclosure({ children }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="debug-disclosure">
      <button
        type="button"
        className="debug-toggle"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>Debug</span>
        <span className={`debug-caret${open ? ' debug-caret-open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>
      {open && <div className="debug-body">{children}</div>}
    </div>
  )
}
