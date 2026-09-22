/**
 * Re-anchoring a saved annotation: find the element it was highlighted in,
 * then the text range its selector names, even after a reload re-rendered it.
 */

import type { AnnotationSource } from './types'

/** The live text range a saved annotation points at, or null if it is not on screen. */
export function rangeForAnnotation(source: AnnotationSource, root: ParentNode = document): Range | null {
  const element = root.querySelector(sourceSelector(source))
  if (!element) return null
  const byOffsets =
    source.start_offset === null || source.end_offset === null
      ? null
      : rangeAtOffsets(element, source.start_offset, source.end_offset)
  if (byOffsets && byOffsets.toString() === source.quote_exact) return byOffsets
  const found = quoteOffset(element.textContent ?? '', source)
  return found === null ? null : rangeAtOffsets(element, found, found + source.quote_exact.length)
}

/** Mirrors the data-annotation-* attributes that `selection.ts` reads. */
function sourceSelector(source: AnnotationSource): string {
  if (source.chat_message_id !== null) {
    return `[data-annotation-source="chat"][data-annotation-message-id="${CSS.escape(source.chat_message_id)}"]`
  }
  const paper = `[data-annotation-source="paper"][data-annotation-paper-id="${source.paper_id}"]`
  return source.paper_chunk_ordinal === null
    ? `${paper}:not([data-annotation-chunk-ordinal])`
    : `${paper}[data-annotation-chunk-ordinal="${source.paper_chunk_ordinal}"]`
}

/** A range over `element`'s text from `start` to `end`, counted in characters. */
function rangeAtOffsets(element: Element, start: number, end: number): Range | null {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
  const range = document.createRange()
  let seen = 0
  let started = false
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const length = (node as Text).length
    if (!started && start <= seen + length) {
      range.setStart(node, start - seen)
      started = true
    }
    if (started && end <= seen + length) {
      range.setEnd(node, end - seen)
      return range
    }
    seen += length
  }
  return null
}

/**
 * Where the quote sits when its offsets have drifted: the occurrence whose
 * preceding text matches the saved prefix, else the first one.
 */
function quoteOffset(text: string, source: AnnotationSource): number | null {
  const quote = source.quote_exact
  let first: number | null = null
  for (let at = text.indexOf(quote); at !== -1; at = text.indexOf(quote, at + 1)) {
    if (!source.quote_prefix || text.slice(0, at).endsWith(source.quote_prefix)) return at
    first ??= at
  }
  return first
}
