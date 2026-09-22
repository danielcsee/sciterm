import { useEffect } from 'react'
import { rangeForAnnotation } from './anchor'
import { clearDefinitionUnderlines, setDefinitionUnderlines } from './selection'
import type { AnnotationDraft } from './types'

/**
 * Underline every annotation's text wherever it is on screen. The page
 * re-renders under us (a paper loading, entity marks, a chat reopening), so
 * this re-anchors after each batch of DOM changes. Setting a CSS highlight
 * does not touch the DOM, so it cannot retrigger the observer.
 */
export function useAnnotationUnderlines(annotations: readonly AnnotationDraft[]): void {
  useEffect(() => watchUnderlines(annotations), [annotations])
}

function watchUnderlines(annotations: readonly AnnotationDraft[]): () => void {
  const underline = () => setDefinitionUnderlines(anchorAll(annotations))
  underline()
  const observer = new MutationObserver(underline)
  observer.observe(document.body, { childList: true, subtree: true, characterData: true })
  return () => {
    observer.disconnect()
    clearDefinitionUnderlines()
  }
}

function anchorAll(annotations: readonly AnnotationDraft[]): Range[] {
  return annotations
    .map((annotation) => rangeForAnnotation(annotation.source))
    .filter((range): range is Range => range !== null)
}
