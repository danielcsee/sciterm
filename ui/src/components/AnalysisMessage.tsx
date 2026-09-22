import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { AnswerEntity, Citation, PaperAnalysisResult, SearchedPaper } from '../api'
import AnalysisAnswer from './AnalysisAnswer'
import CitationList from './CitationList'
import DebugDisclosure from './DebugDisclosure'

interface Props {
  analysis: PaperAnalysisResult
  papers: SearchedPaper[]
  /** The answer is still being written. */
  pending: boolean
  /** Entities the answer names, once found. */
  entities: AnswerEntity[]
  /** The answer is finished, but its entities are still being found. */
  entitiesPending: boolean
  /** Why no answer is shown: the message text, once the answer has failed. */
  fallbackText: string
  /** The newest message: only it keeps room below its answer. */
  isLatest: boolean
  onOpenPaper: (paperId: number, title: string | null) => void
  onOpenCitation: (citation: Citation) => void
  onSmartGroupCreated: () => void
}

/** Room kept above the answer when it is scrolled to the top. */
const ANSWER_TOP_GAP = 16

/**
 * A `paper_analysis` reply: the citations, folded, then the answer streaming
 * in below. A spinner trails the answer until its last word and its entity
 * underlines have both arrived.
 *
 * When the answer's first words arrive, it is scrolled to the top of the chat
 * once, and then left alone: the rest runs off the bottom for the reader to
 * scroll to. A browser cannot scroll an element to the top without enough
 * content beneath it, so the newest answer is floored at the chat's height.
 */
export default function AnalysisMessage({
  analysis,
  papers,
  pending,
  entities,
  entitiesPending,
  fallbackText,
  isLatest,
  onOpenPaper,
  onOpenCitation,
  onSmartGroupCreated,
}: Props) {
  const answerRef = useRef<HTMLDivElement>(null)
  // Only an answer that streams in while this is mounted is scrolled to;
  // one that was already whole never is.
  const startedEmpty = useRef(!analysis.answer)
  const [floor, setFloor] = useState<number | null>(null)
  const started = startedEmpty.current && Boolean(analysis.answer)

  useLayoutEffect(() => {
    if (!started || floor !== null || !answerRef.current) return
    setFloor(answerFloor(answerRef.current))
  }, [started, floor])

  useEffect(() => {
    if (floor === null) return
    answerRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [floor])

  return (
    <>
      {analysis.citations.length > 0 && (
        <DebugDisclosure label="Citations">
          <CitationList
            citations={analysis.citations}
            papers={papers}
            onOpenPaper={onOpenPaper}
            onOpenCitation={onOpenCitation}
          />
        </DebugDisclosure>
      )}
      <div
        ref={answerRef}
        className="analysis-block"
        style={{
          scrollMarginTop: ANSWER_TOP_GAP,
          minHeight: isLatest && floor !== null ? floor : undefined,
        }}
      >
        {analysis.answer ? (
          <AnalysisAnswer
            answer={analysis.answer}
            citations={analysis.citations}
            entities={entities}
            onOpenCitation={onOpenCitation}
            onSmartGroupCreated={onSmartGroupCreated}
            trailing={
              (pending || entitiesPending) && (
                <span className="spinner spinner-inline" role="status" aria-label="Loading" />
              )
            }
          />
        ) : pending ? (
          <span className="rag-pending" role="status">
            <span className="spinner" aria-hidden="true" />
            <span>Writing an answer…</span>
          </span>
        ) : (
          <p className="rag-text">{fallbackText}</p>
        )}
      </div>
    </>
  )
}

/** The height that lets `element` be scrolled to the top of its scroller. */
function answerFloor(element: HTMLElement): number {
  const scroller = element.closest('.chat-scroll')
  return Math.max(0, (scroller?.clientHeight ?? 0) - ANSWER_TOP_GAP)
}
