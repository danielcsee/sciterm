import { useHighlight } from './useHighlight'
import type { Highlight } from './selection'

interface Props {
  onDefine: (highlight: Highlight) => void
}

/**
 * "Define this term", level with the first highlighted line in the gutter to
 * the right of the text. Rendered only while there is a highlight to define.
 */
export default function DefineTermButton({ onDefine }: Props) {
  const highlight = useHighlight()
  if (!highlight) return null

  return (
    <button
      type="button"
      className="define-term-button"
      style={{ top: highlight.top, left: highlight.left, maxWidth: highlight.maxWidth }}
      // Keep the highlight: a mousedown on a button would otherwise clear it.
      onMouseDown={(event) => event.preventDefault()}
      onClick={() => onDefine(highlight)}
    >
      Define this term
    </button>
  )
}
