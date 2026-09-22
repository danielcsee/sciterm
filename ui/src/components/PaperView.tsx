import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  ApiError,
  fetchPaper,
  isHeading,
  type EntitySpan,
  type PaperDetail,
  type PaperEntity,
} from '../api'
import type { PaperFocus } from '../types'
import { toSegments, type Segment } from '../highlight'
import { sectionLabel } from '../sections'
import PaperEntities from './PaperEntities'

interface Props {
  paperId: number
  /** Show this paper's references in the side panel. */
  onViewReferences?: (paperId: number, title: string) => void
  /** Show imported papers that reference this paper in the side panel. */
  onViewImportedReferences?: (paperId: number, title: string) => void
  /** Lets the tab title update once the full title arrives. */
  onLoaded?: (paper: PaperDetail) => void
  /** The paper is gone (404), so its tab should not outlive this session. */
  onMissing?: (paperId: number) => void
  /** Scroll to this paragraph and highlight these entities once loaded. */
  focus?: PaperFocus | null
  /** The focus has been applied, so the caller can let go of it. */
  onFocusApplied?: () => void
}

/**
 * Index of the first mark in or after paragraph `ordinal`, in the document
 * order the marks are numbered in; 0 when none follows.
 */
function firstMarkFrom(
  paragraphs: Map<number, { firstMark: number }>,
  ordinal: number,
): number {
  let best: { ordinal: number; firstMark: number } | null = null
  for (const [candidate, entry] of paragraphs) {
    if (candidate >= ordinal && (best === null || candidate < best.ordinal)) {
      best = { ordinal: candidate, firstMark: entry.firstMark }
    }
  }
  return best?.firstMark ?? 0
}

function formatReference(reference: {
  source: string | null
  year: string | null
  volume: string | null
  fpage: string | null
  lpage: string | null
}): string {
  const pages = [reference.fpage, reference.lpage].filter(Boolean).join('–')
  return [reference.source, reference.year, reference.volume, pages]
    .filter(Boolean)
    .join(' · ')
}

/** One stored paper, laid out for reading. */
export default function PaperView({
  paperId,
  onViewReferences,
  onViewImportedReferences,
  onLoaded,
  onMissing,
  focus,
  onFocusApplied,
}: Props) {
  const [paper, setPaper] = useState<PaperDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Highlighted entities: one clicked pill, or every query entity of a citation.
  const [selected, setSelected] = useState<PaperEntity[]>([])
  // The paper's entities, reported by PaperEntities; null until loaded. A
  // citation's entity ids resolve to spans through this.
  const [entities, setEntities] = useState<PaperEntity[] | null>(null)
  // The cited paragraph, outlined until the reader picks something else.
  const [focusedOrdinal, setFocusedOrdinal] = useState<number | null>(null)
  // Handed from the focus effect to the layout effect below, which scrolls
  // there instead of to the first mark once the new marks are rendered.
  const pendingOrdinal = useRef<number | null>(null)
  // Where each mark sits in the document, as a fraction of scrollable height.
  // Measured from the DOM rather than derived from offsets: only the rendered
  // marks are navigable, and only layout knows how tall a paragraph became.
  const [markFractions, setMarkFractions] = useState<number[]>([])
  const [current, setCurrent] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Spans arrive in reading order for the whole paper; the renderer wants them
  // per paragraph, so bucket once per selection rather than filtering 634 of
  // them inside every paragraph on every render.
  const spansByOrdinal = useMemo(() => {
    const byOrdinal = new Map<number, EntitySpan[]>()
    for (const span of selected.flatMap((entity) => entity.spans)) {
      const bucket = byOrdinal.get(span.ordinal)
      if (bucket) bucket.push(span)
      else byOrdinal.set(span.ordinal, [span])
    }
    return byOrdinal
  }, [selected])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchPaper(paperId, controller.signal)
      .then((loaded) => {
        setPaper(loaded)
        onLoaded?.(loaded)
      })
      .catch((err: unknown) => {
        if ((err as Error)?.name === 'AbortError') return
        setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
        // 404 means the paper left the corpus. Keep the tab for this session so
        // the reader sees why, but tell App to stop persisting it.
        if (err instanceof ApiError && err.status === 404) onMissing?.(paperId)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
    // onLoaded is a fresh closure each render; re-fetching on it would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paperId])

  // Segments, computed once per selection rather than per render, with each
  // highlighted run numbered in document order. That numbering has to match the
  // order `querySelectorAll('.entity-mark')` returns, since the chevrons and the
  // scroll map both index into that.
  const paragraphSegments = useMemo(() => {
    const byOrdinal = new Map<number, { segments: Segment[]; firstMark: number }>()
    let seen = 0
    for (const paragraph of paper?.paragraphs ?? []) {
      const spans = spansByOrdinal.get(paragraph.ordinal)
      if (!spans) continue
      const segments = toSegments(paragraph.text, spans)
      byOrdinal.set(paragraph.ordinal, { segments, firstMark: seen })
      seen += segments.filter((segment) => segment.highlighted).length
    }
    return byOrdinal
  }, [paper, spansByOrdinal])

  // A different paper starts at its own top, not where the last one was left.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
    setSelected([])
    setFocusedOrdinal(null)
  }, [paperId])

  // Apply a citation once both the paper and its entities are in: select the
  // query's entities and queue the scroll, which the layout effect performs
  // after the marks exist. A fresh `focus` object re-applies, so clicking the
  // same citation again scrolls back to it.
  useEffect(() => {
    if (!focus || !paper || entities === null) return
    const wanted = new Set(focus.entityIds)
    pendingOrdinal.current = focus.ordinal
    setFocusedOrdinal(focus.ordinal)
    setSelected(entities.filter((entity) => wanted.has(entity.entity_id)))
    onFocusApplied?.()
  }, [focus, paper, entities, onFocusApplied])

  const selectEntity = useCallback((entity: PaperEntity | null) => {
    setFocusedOrdinal(null)
    setSelected(entity ? [entity] : [])
  }, [])

  const clearHighlight = useCallback(() => {
    setFocusedOrdinal(null)
    setSelected([])
  }, [])

  const marksIn = (container: HTMLElement) =>
    Array.from(container.querySelectorAll<HTMLElement>('.entity-mark'))

  /** Scroll one occurrence into view and make it the current one. */
  const goTo = useCallback((index: number) => {
    const container = scrollRef.current
    if (!container) return
    const marks = marksIn(container)
    if (marks.length === 0) return
    // Wrap, the way find-next does: with 315 occurrences, stopping dead at
    // the last one is more annoying than looping.
    const wrapped = ((index % marks.length) + marks.length) % marks.length
    marks[wrapped].scrollIntoView({ block: 'center' })
    setCurrent(wrapped)
  }, [])

  /** Where every mark sits, as a fraction of the scrollable height. */
  const measureMarks = useCallback(() => {
    const container = scrollRef.current
    if (!container) return
    const containerTop = container.getBoundingClientRect().top
    const height = container.scrollHeight || 1
    setMarkFractions(
      marksIn(container).map((mark) => {
        const offset = mark.getBoundingClientRect().top - containerTop + container.scrollTop
        return Math.min(1, Math.max(0, offset / height))
      }),
    )
  }, [])

  // Measure the marks, then take the reader to the cited paragraph if one is
  // pending, or else to the first mark.
  //
  // Instant, not smooth. The first mention can be 4,000px down, which is a long
  // disorienting slide rather than a helpful one — and `behavior: 'smooth'`
  // measured as a no-op here, so it would have silently done nothing at all.
  useLayoutEffect(() => {
    measureMarks()
    const target = pendingOrdinal.current
    pendingOrdinal.current = null
    if (target !== null) {
      setCurrent(firstMarkFrom(paragraphSegments, target))
      scrollRef.current
        ?.querySelector(`[data-ordinal="${target}"]`)
        ?.scrollIntoView({ block: 'start' })
      return
    }
    setCurrent(0)
    if (selected.length === 0) return
    scrollRef.current?.querySelector('.entity-mark')?.scrollIntoView({ block: 'center' })
    // paragraphSegments follows `selected`; it is read here, never a trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, measureMarks])

  // Reflow moves every mark, so the ticks would otherwise point at where the
  // text used to be.
  useEffect(() => {
    if (selected.length === 0) return
    const onResize = () => measureMarks()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [selected, measureMarks])

  // Escape clears the highlight, the usual way out of a mode.
  useEffect(() => {
    if (selected.length === 0 && focusedOrdinal === null) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') clearHighlight()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, focusedOrdinal, clearHighlight])

  if (loading) {
    return (
      <section className="paper" aria-busy="true">
        <div className="paper-scroll">
          <div className="results-loading" role="status">
            <span className="spinner" aria-hidden="true" />
            <span>Loading paper…</span>
          </div>
        </div>
      </section>
    )
  }

  if (error || !paper) {
    return (
      <section className="paper">
        <div className="paper-scroll">
          <p className="results-message results-error">{error ?? 'Paper unavailable.'}</p>
        </div>
      </section>
    )
  }

  const citation = [
    paper.journal_title ?? paper.journal,
    paper.pub_year,
    paper.volume && `vol. ${paper.volume}`,
    [paper.fpage, paper.lpage].filter(Boolean).join('–'),
  ]
    .filter(Boolean)
    .join(' · ')

  let lastSection: string | null = null

  return (
    <section className="paper paper-with-entities" aria-label={paper.title ?? 'Paper'}>
      <PaperEntities
        paperId={paper.paper_id}
        selectedIds={new Set(selected.map((entity) => entity.entity_id))}
        onSelect={selectEntity}
        onEntitiesLoaded={setEntities}
        nav={
          selected.length > 0
            ? {
                current: markFractions.length === 0 ? 0 : current + 1,
                total: markFractions.length,
                onPrevious: () => goTo(current - 1),
                onNext: () => goTo(current + 1),
              }
            : null
        }
      />
      <div className="paper-reader">
        <div className="paper-scroll" ref={scrollRef} data-definable>
        <article className="paper-doc" data-definable-column>
          <header
            className="paper-doc-header"
            data-annotation-source="paper"
            data-annotation-paper-id={paper.paper_id}
          >
            <h1 className="paper-doc-title">{paper.title ?? 'Untitled'}</h1>
            {paper.authors.length > 0 && (
              <p className="paper-doc-authors">{paper.authors.join(', ')}</p>
            )}
            {citation && <p className="paper-doc-citation">{citation}</p>}
            <p className="paper-doc-ids">
              <span>
                {[
                  `PMID ${paper.pmid}`,
                  paper.pmcid,
                  paper.doi ? `doi:${paper.doi}` : null,
                  paper.has_full_text ? null : 'abstract only',
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
              {(onViewReferences || onViewImportedReferences) && (
                <span className="paper-doc-links">
                  {onViewReferences && paper.references.length > 0 && (
                    <button
                      type="button"
                      className="paper-doc-refs-link"
                      onClick={() => onViewReferences(paper.paper_id, paper.title ?? 'this paper')}
                    >
                      view references ({paper.references.length})
                    </button>
                  )}
                  {onViewImportedReferences && (
                    <button
                      type="button"
                      className="paper-doc-refs-link"
                      onClick={() =>
                        onViewImportedReferences(paper.paper_id, paper.title ?? 'this paper')
                      }
                    >
                      imported references ({paper.imported_reference_count})
                    </button>
                  )}
                </span>
              )}
            </p>
          </header>

          {paper.paragraphs.map((paragraph) => {
            // A rule whenever the section changes, so the document reads as
            // sections rather than an undifferentiated wall of paragraphs.
            const startsSection =
              paragraph.section_type !== null && paragraph.section_type !== lastSection
            const label = startsSection
              ? sectionLabel(paragraph.section_type as string)
              : null
            lastSection = paragraph.section_type ?? lastSection

            // Without a selection this is the same single text node as
            // before, so the ordinary reading path is untouched.
            const entry = paragraphSegments.get(paragraph.ordinal)
            let markIndex = entry?.firstMark ?? 0
            const body = entry
              ? entry.segments.map((segment, index) => {
                  if (!segment.highlighted) return <span key={index}>{segment.text}</span>
                  const isCurrent = markIndex++ === current
                  return (
                    <mark
                      key={index}
                      className={`entity-mark${isCurrent ? ' entity-mark-current' : ''}`}
                    >
                      {segment.text}
                    </mark>
                  )
                })
              : paragraph.text

            return (
              <div
                key={paragraph.ordinal}
                data-ordinal={paragraph.ordinal}
                data-annotation-source="paper"
                data-annotation-paper-id={paper.paper_id}
                data-annotation-chunk-ordinal={paragraph.ordinal}
                className={
                  paragraph.ordinal === focusedOrdinal ? 'paper-doc-focus' : undefined
                }
              >
                {label && <h2 className="paper-doc-section">{label}</h2>}
                {isHeading(paragraph) ? (
                  <h3 className="paper-doc-heading">{body}</h3>
                ) : (
                  <p className="paper-doc-para">{body}</p>
                )}
              </div>
            )
          })}

          {paper.references.length > 0 && (
            <section className="paper-doc-refs">
              <h2 className="paper-doc-section">References</h2>
              <ol className="paper-doc-reflist">
                {paper.references.map((reference) => (
                  <li key={reference.ordinal}>
                    <span className="paper-ref-title">{reference.title ?? 'Untitled'}</span>
                    <span className="paper-ref-meta">
                      {[
                        formatReference(reference),
                        reference.pmid ? `PMID ${reference.pmid}` : null,
                        reference.doi ? `doi:${reference.doi}` : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </article>
        </div>
        {markFractions.length > 0 && (
          // A minimap of the scrollbar: one tick per occurrence, so the reader
          // can see how far the next one is before scrolling for it.
          <div className="paper-scrollmap" aria-hidden="true">
            {markFractions.map((fraction, index) => (
              <span
                key={index}
                className={`scrollmap-tick${
                  index === current ? ' scrollmap-tick-current' : ''
                }`}
                style={{ top: `${fraction * 100}%` }}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
