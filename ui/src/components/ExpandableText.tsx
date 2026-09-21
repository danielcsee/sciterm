import { useState } from 'react'

/** Characters shown before the rest is folded away. */
export const PREVIEW_CHARS = 300

interface Props {
  text: string
  /** Characters shown while collapsed. */
  previewChars?: number
}

/** The collapsed head of `text`, or null when it already fits. */
export function previewOf(text: string, previewChars: number): string | null {
  if (text.length <= previewChars) return null
  return `${text.slice(0, previewChars).trimEnd()}…`
}

/**
 * Text cut to its first `previewChars` characters, with a toggle styled like
 * `DebugDisclosure` that reveals the rest. Collapsed by default; text short
 * enough to fit renders whole, with no toggle.
 */
export default function ExpandableText({ text, previewChars = PREVIEW_CHARS }: Props) {
  const [open, setOpen] = useState(false)
  const preview = previewOf(text, previewChars)
  if (preview === null) return <>{text}</>

  return (
    <>
      {open ? text : preview}
      <button
        type="button"
        className="debug-toggle expandable-toggle"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>{open ? 'Less' : 'More'}</span>
        <span className={`debug-caret${open ? ' debug-caret-open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>
    </>
  )
}
