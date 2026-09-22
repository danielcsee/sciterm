/**
 * Reading a highlight out of the DOM: its text, the paragraph around it, and
 * where the "Define this term" button can sit beside it without covering text.
 */

/** Highlights longer than this carry their own context; none is sent. */
export const MAX_CONTEXT_WORDS = 12

/** Space kept between the text column, the button and the container edge. */
const GUTTER_GAP = 12
/** Narrower than this and the button cannot fit beside the text. */
export const MIN_GUTTER_WIDTH = 64

/** Marks a scrolling region whose text can be defined. */
export const DEFINABLE_ATTR = 'data-definable'
/** Marks the text column inside it; the gutter is what lies to its right. */
export const DEFINABLE_COLUMN_ATTR = 'data-definable-column'
/** CSS Custom Highlight name for the phrase whose definition is open. */
export const DEFINITION_UNDERLINE = 'definition-request'

const BLOCK_SELECTOR = 'p, li, h1, h2, h3, h4, h5, h6, blockquote, dd, td, th, figcaption'
/** Blank lines inside one element (the chat answer is one pre-wrap <p>). */
const PARAGRAPH_BREAK = /\n\s*\n/

export interface Highlight {
  phrase: string
  surroundingContext: string | null
  /** A stable copy of the selected text range, retained after selection changes. */
  range: Range
  /** Viewport position for the button: the first highlighted line, in the gutter. */
  top: number
  left: number
  maxWidth: number
  source: HighlightSource
  selector: TextSelector
}

export type HighlightSource =
  | { kind: 'chat'; messageId: string; sourceKey: string }
  | { kind: 'paper'; paperId: number; chunkOrdinal: number | null; sourceKey: string }

export interface TextSelector {
  quoteExact: string
  quotePrefix: string | null
  quoteSuffix: string | null
  startOffset: number
  endOffset: number
}

export function countWords(text: string): number {
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

/** The current highlight inside a definable region, or null when there is none. */
export function readHighlight(selection: Selection | null): Highlight | null {
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null
  const range = selection.getRangeAt(0)
  const phrase = selection.toString().trim().replace(/\s+/g, ' ')
  if (!phrase) return null

  const container = closestElement(range.commonAncestorContainer, `[${DEFINABLE_ATTR}]`)
  if (!container) return null
  const sourceElement = annotationSource(range)
  if (!sourceElement) return null
  const source = sourceFromElement(sourceElement)
  if (!source) return null
  const placement = gutterPlacement(range, container)
  if (!placement) return null

  const surroundingContext =
    countWords(phrase) > MAX_CONTEXT_WORDS ? null : paragraphAround(range, container)
  return {
    phrase,
    surroundingContext,
    range: range.cloneRange(),
    source,
    selector: textSelector(range, sourceElement),
    ...placement,
  }
}

function annotationSource(range: Range): Element | null {
  const start = closestElement(range.startContainer, '[data-annotation-source]')
  const end = closestElement(range.endContainer, '[data-annotation-source]')
  return start && start === end ? start : null
}

function sourceFromElement(element: Element): HighlightSource | null {
  const kind = element.getAttribute('data-annotation-source')
  if (kind === 'chat') {
    const messageId = element.getAttribute('data-annotation-message-id')
    return messageId
      ? { kind, messageId, sourceKey: `message:${messageId}` }
      : null
  }
  if (kind === 'paper') {
    const paperId = Number(element.getAttribute('data-annotation-paper-id'))
    const ordinalValue = element.getAttribute('data-annotation-chunk-ordinal')
    const chunkOrdinal = ordinalValue === null ? null : Number(ordinalValue)
    if (!Number.isInteger(paperId) || paperId < 1) return null
    return {
      kind,
      paperId,
      chunkOrdinal,
      sourceKey: chunkOrdinal === null ? `paper:${paperId}:header` : `paper:${paperId}:chunk:${chunkOrdinal}`,
    }
  }
  return null
}

function textSelector(range: Range, source: Element): TextSelector {
  const before = document.createRange()
  before.selectNodeContents(source)
  before.setEnd(range.startContainer, range.startOffset)
  const startOffset = before.toString().length
  const quoteExact = range.toString()
  const sourceText = source.textContent ?? ''
  const endOffset = startOffset + quoteExact.length
  return {
    quoteExact,
    quotePrefix: sourceText.slice(Math.max(0, startOffset - 100), startOffset) || null,
    quoteSuffix: sourceText.slice(endOffset, endOffset + 100) || null,
    startOffset,
    endOffset,
  }
}

/** Keep the requested phrase visibly tied to the definition shown in the sidebar. */
export function underlineDefinitionRange(range: Range): void {
  if (!('highlights' in CSS) || typeof globalThis.Highlight === 'undefined') return
  const underline = CSS.highlights.get(DEFINITION_UNDERLINE)
  if (underline) {
    underline.add(range)
    return
  }
  CSS.highlights.set(DEFINITION_UNDERLINE, new globalThis.Highlight(range))
}

export function clearDefinitionUnderline(): void {
  if (!('highlights' in CSS)) return
  CSS.highlights.delete(DEFINITION_UNDERLINE)
}

/**
 * Beside the first highlighted line, right of the text column. Null when that
 * line has scrolled out of the container, or there is no gutter wide enough.
 */
function gutterPlacement(
  range: Range,
  container: Element,
): Pick<Highlight, 'top' | 'left' | 'maxWidth'> | null {
  const line = firstLineRect(range)
  const bounds = container.getBoundingClientRect()
  if (!line || line.bottom < bounds.top || line.top > bounds.bottom) return null

  const column =
    closestElement(range.commonAncestorContainer, `[${DEFINABLE_COLUMN_ATTR}]`) ??
    container.querySelector(`[${DEFINABLE_COLUMN_ATTR}]`)
  const textRight = column ? column.getBoundingClientRect().right : line.right
  const left = textRight + GUTTER_GAP
  // clientWidth leaves out the scrollbar, so the button never sits on it.
  const right = bounds.left + container.clientWidth - GUTTER_GAP
  const maxWidth = right - left
  if (maxWidth < MIN_GUTTER_WIDTH) return null
  return { top: line.top, left, maxWidth }
}

function firstLineRect(range: Range): DOMRect | null {
  // A selection that starts at the end of a line reports an empty first rect.
  for (const rect of range.getClientRects()) {
    if (rect.width > 0 && rect.height > 0) return rect
  }
  return null
}

/**
 * The paragraph the highlight starts in, plus the one it ends in if that is
 * different. Null when the highlight is not inside any paragraph-like block.
 */
function paragraphAround(range: Range, container: Element): string | null {
  const start = blockParagraph(range.startContainer, range.startOffset, container)
  const end = blockParagraph(range.endContainer, range.endOffset, container)
  const paragraphs = [start, end].filter((text): text is string => !!text)
  const unique = [...new Set(paragraphs)]
  return unique.length ? unique.join('\n\n') : null
}

/** The paragraph containing one boundary point of the highlight. */
function blockParagraph(node: Node, offset: number, container: Element): string | null {
  const block = closestElement(node, BLOCK_SELECTOR)
  if (!block || !container.contains(block)) return null
  const before = document.createRange()
  before.setStart(block, 0)
  before.setEnd(node, offset)
  return paragraphAt(block.textContent ?? '', before.toString().length)
}

/** The blank-line-separated paragraph of `text` that contains `offset`. */
export function paragraphAt(text: string, offset: number): string | null {
  let cursor = 0
  for (const part of text.split(PARAGRAPH_BREAK)) {
    const found = text.indexOf(part, cursor)
    const end = found + part.length
    if (offset <= end) return part.trim() || null
    cursor = end
  }
  return text.trim() || null
}

function closestElement(node: Node, selector: string): Element | null {
  const element = node instanceof Element ? node : node.parentElement
  return element?.closest(selector) ?? null
}
