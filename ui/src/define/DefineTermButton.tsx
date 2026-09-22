import { useHighlight } from './useHighlight'

interface Props {
  onDefine: (phrase: string, surroundingContext: string | null, range: Range) => void
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
      onClick={() => onDefine(highlight.phrase, highlight.surroundingContext, highlight.range)}
    >
      Define this term
    </button>
  )
}
