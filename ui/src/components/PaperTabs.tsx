import { useCallback, useEffect, useRef, useState } from 'react'
import {
  tabKey,
  tabView,
  truncateTitle,
  viewKey,
  type OpenTab,
  type TabView,
  type View,
} from '../navigation'

interface Props {
  tabs: OpenTab[]
  active: View
  /** Paper tabs briefly wearing the selected styling after being opened in
      the background. Purely visual — they are not selected. */
  flashing: ReadonlySet<number>
  onSelect: (view: TabView) => void
  onClose: (view: TabView) => void
}

/**
 * The scrolling half of the tab bar: open papers and saved conversations.
 *
 * Separate from the My Corpus tab on purpose: that one must stay put while
 * these scroll, and the only way to guarantee that is for the overflow to live
 * on a container that does not include it.
 */
export default function PaperTabs({
  tabs,
  active,
  flashing,
  onSelect,
  onClose,
}: Props) {
  const stripRef = useRef<HTMLDivElement>(null)
  const [overflowing, setOverflowing] = useState(false)
  const activeKey = viewKey(active)

  // The fade means "there is more to the right", so it must appear only when
  // that is true — not whenever the strip happens to be narrower than its slot.
  const measure = useCallback(() => {
    const strip = stripRef.current
    if (!strip) return
    const remaining = strip.scrollWidth - strip.clientWidth - strip.scrollLeft
    setOverflowing(remaining > 1)
  }, [])

  useEffect(() => {
    measure()
    const strip = stripRef.current
    if (!strip) return
    const observer = new ResizeObserver(measure)
    observer.observe(strip)
    strip.addEventListener('scroll', measure, { passive: true })
    return () => {
      observer.disconnect()
      strip.removeEventListener('scroll', measure)
    }
  }, [measure, tabs.length])

  // A newly opened tab is appended off-screen once the strip overflows; bring
  // the selected one into view rather than making the user hunt for it.
  useEffect(() => {
    stripRef.current
      ?.querySelector(`[data-tab-key="${activeKey}"]`)
      ?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [activeKey, tabs.length])

  if (tabs.length === 0) return null

  return (
    <div className="paper-tabs">
      <div className="paper-tabs-strip" ref={stripRef} role="tablist" aria-label="Open tabs">
        {tabs.map((tab) => {
          const key = tabKey(tab)
          const selected = key === activeKey
          const flash = tab.kind === 'paper' && flashing.has(tab.paperId)
          return (
            <span
              key={key}
              className={`paper-tab${selected ? ' paper-tab-active' : ''}${
                flash ? ' paper-tab-flash' : ''
              }`}
              data-tab-key={key}
            >
              <button
                type="button"
                role="tab"
                aria-selected={selected}
                className="paper-tab-label"
                title={tab.title}
                onClick={() => onSelect(tabView(tab))}
              >
                {truncateTitle(tab.title)}
              </button>
              <button
                type="button"
                className="paper-tab-close"
                aria-label={`Close ${tab.title}`}
                onClick={() => onClose(tabView(tab))}
              >
                ✕
              </button>
            </span>
          )
        })}
      </div>
      {/* Signals that there is more to the right once the strip overflows. */}
      {overflowing && <span className="paper-tabs-fade" aria-hidden="true" />}
    </div>
  )
}
