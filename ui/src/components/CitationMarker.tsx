import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import type { Citation } from '../api'
import { sectionLabel } from '../sections'

interface Props {
  citation: Citation
  onOpen: (citation: Citation) => void
  /** Visible content; defaults to "[n]". */
  children?: ReactNode
  className?: string
}

/** Viewport box of the marker the tooltip describes. */
interface Anchor {
  left: number
  right: number
  top: number
  bottom: number
}

/** Keep the tooltip this far from the marker and from the viewport edge. */
const TIP_GAP = 8

/**
 * A citation: hovering or focusing shows the cited paragraph, clicking opens
 * the paper scrolled to it.
 *
 * The tooltip is `position: fixed` and placed in a layout effect, as in
 * `PaperEntities`: the chat scrolls, and an absolutely-positioned child would
 * be clipped by it. It sits above the marker, or below when there is no room.
 */
export default function CitationMarker({ citation, onOpen, children, className }: Props) {
  const [anchor, setAnchor] = useState<Anchor | null>(null)
  const tipRef = useRef<HTMLDivElement>(null)

  // A tooltip pinned to the viewport would hang in place while the chat
  // scrolls out from under it.
  useEffect(() => {
    if (!anchor) return
    const dismiss = () => setAnchor(null)
    window.addEventListener('scroll', dismiss, { passive: true, capture: true })
    window.addEventListener('resize', dismiss)
    return () => {
      window.removeEventListener('scroll', dismiss, { capture: true })
      window.removeEventListener('resize', dismiss)
    }
  }, [anchor])

  useLayoutEffect(() => {
    const element = tipRef.current
    if (element && anchor) placeTip(element, anchor)
  }, [anchor])

  function show(element: HTMLElement) {
    const box = element.getBoundingClientRect()
    setAnchor({ left: box.left, right: box.right, top: box.top, bottom: box.bottom })
  }

  return (
    <>
      <button
        type="button"
        className={className ?? 'citation-marker'}
        onClick={() => {
          setAnchor(null)
          onOpen(citation)
        }}
        onMouseEnter={(event) => show(event.currentTarget)}
        onMouseLeave={() => setAnchor(null)}
        onFocus={(event) => show(event.currentTarget)}
        onBlur={() => setAnchor(null)}
        aria-label={`Citation ${citation.number}: open the paper at this paragraph`}
      >
        {children ?? `[${citation.number}]`}
      </button>
      {anchor && (
        <div
          className="citation-tip"
          role="tooltip"
          ref={tipRef}
          // Hidden until placed, so it never flashes at the top-left corner.
          style={{ visibility: 'hidden' }}
        >
          <span className="citation-tip-meta">
            [{citation.number}]
            {citation.section_type && ` · ${sectionLabel(citation.section_type)}`}
          </span>
          <span className="citation-tip-text">{citation.text}</span>
        </div>
      )}
    </>
  )
}

/** Centre the tooltip over the marker, flipping below when it will not fit. */
function placeTip(element: HTMLElement, anchor: Anchor) {
  const box = element.getBoundingClientRect()
  const centred = (anchor.left + anchor.right) / 2 - box.width / 2
  const maxLeft = window.innerWidth - box.width - TIP_GAP
  element.style.left = `${Math.max(TIP_GAP, Math.min(centred, maxLeft))}px`
  const above = anchor.top - box.height - TIP_GAP
  element.style.top = above >= TIP_GAP ? `${above}px` : `${anchor.bottom + TIP_GAP}px`
  element.style.visibility = 'visible'
}
