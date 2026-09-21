import type { Citation } from '../api'
import CitationMarker from './CitationMarker'

interface Props {
  answer: string
  citations: Citation[]
  onOpenCitation: (citation: Citation) => void
}

/** A piece of the answer: prose, or one citation number. */
export type AnswerPart = { kind: 'text'; text: string } | { kind: 'cite'; number: number }

/** "[1]", "[1][3]" and "[1, 3]" all cite; the model is asked for the first two. */
const CITE_RE = /\[(\d+(?:\s*,\s*\d+)*)\]/g

/**
 * Split an answer into prose and citation numbers.
 *
 * A number the answer cites but the response never supplied stays as literal
 * text: a marker that opens nothing is worse than none.
 */
export function splitCitations(answer: string, known: ReadonlySet<number>): AnswerPart[] {
  const parts: AnswerPart[] = []
  let cursor = 0
  for (const match of answer.matchAll(CITE_RE)) {
    const numbers = match[1].split(',').map((value) => Number(value.trim()))
    if (!numbers.every((number) => known.has(number))) continue
    if (match.index > cursor) parts.push({ kind: 'text', text: answer.slice(cursor, match.index) })
    for (const number of numbers) parts.push({ kind: 'cite', number })
    cursor = match.index + match[0].length
  }
  if (cursor < answer.length) parts.push({ kind: 'text', text: answer.slice(cursor) })
  return parts
}

/** The generated answer, with each `[n]` a live citation marker. */
export default function AnalysisAnswer({ answer, citations, onOpenCitation }: Props) {
  const byNumber = new Map(citations.map((citation) => [citation.number, citation]))
  const parts = splitCitations(answer, new Set(byNumber.keys()))

  return (
    <p className="rag-text analysis-answer">
      {parts.map((part, index) =>
        part.kind === 'text' ? (
          <span key={index}>{part.text}</span>
        ) : (
          <CitationMarker
            key={index}
            citation={byNumber.get(part.number) as Citation}
            onOpen={onOpenCitation}
          />
        ),
      )}
    </p>
  )
}
