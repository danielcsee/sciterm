import { useEffect, useState } from 'react'
import { readHighlight, type Highlight } from './selection'

/**
 * The reader's current highlight, re-measured as they scroll or resize.
 *
 * Nothing is reported mid-drag: the button would chase the pointer. It
 * appears when the mouse is released, or as a keyboard selection changes.
 */
export function useHighlight(): Highlight | null {
  const [highlight, setHighlight] = useState<Highlight | null>(null)

  useEffect(() => {
    let dragging = false
    let frame = 0

    const measure = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => setHighlight(readHighlight(document.getSelection())))
    }
    const onPointerDown = (event: PointerEvent) => {
      if (event.button === 0) dragging = true
    }
    const onPointerUp = () => {
      dragging = false
      measure()
    }
    const onSelectionChange = () => {
      if (!dragging) measure()
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('pointerup', onPointerUp)
    document.addEventListener('selectionchange', onSelectionChange)
    // Capture: scroll does not bubble, and the text scrolls inside its panel.
    window.addEventListener('scroll', measure, true)
    window.addEventListener('resize', measure)
    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('pointerup', onPointerUp)
      document.removeEventListener('selectionchange', onSelectionChange)
      window.removeEventListener('scroll', measure, true)
      window.removeEventListener('resize', measure)
    }
  }, [])

  return highlight
}
