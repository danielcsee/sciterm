import { useState, type ReactNode } from 'react'
import type { AnswerEntity, Citation } from '../api'
import { markPhrases } from '../entityPhrases'
import AnswerEntityPills from './AnswerEntityPills'
import CitationMarker from './CitationMarker'

interface Props {
  answer: string
  citations: Citation[]
  /**
   * Entities the answer names, listed as pills after it; hovering a pill
   * underlines each phrase naming that entity.
   */
  entities: AnswerEntity[]
  onOpenCitation: (citation: Citation) => void
  /** Drawn after the last word, e.g. a spinner while more is coming. */
  trailing?: ReactNode
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

/**
 * The generated answer, with each `[n]` a live citation marker, followed by a
 * pill per recognised entity. Only the hovered pill's phrases are underlined.
 */
export default function AnalysisAnswer({
  answer,
  citations,
  entities,
  onOpenCitation,
  trailing,
}: Props) {
  const byNumber = new Map(citations.map((citation) => [citation.number, citation]))
  const parts = splitCitations(answer, new Set(byNumber.keys()))
  const [activeId, setActiveId] = useState<number | null>(null)
  const active = entities.find((entity) => entity.entity_id === activeId) ?? null

  return (
    <>
      <p className="rag-text analysis-answer">
        {parts.map((part, index) =>
          part.kind === 'text' ? (
            <span key={index}>
              <EntityPhrases text={part.text} entity={active} />
            </span>
          ) : (
            <CitationMarker
              key={index}
              citation={byNumber.get(part.number) as Citation}
              onOpen={onOpenCitation}
            />
          ),
        )}
        {trailing}
      </p>
      <AnswerEntityPills entities={entities} onActivate={setActiveId} />
    </>
  )
}

interface EntityPhrasesProps {
  text: string
  /** The hovered pill's entity, or null when no pill is hovered. */
  entity: AnswerEntity | null
}

/**
 * One stretch of prose, with the hovered entity's phrases underlined.
 *
 * Only that entity's phrases are matched. Two entities often share a phrase
 * (MeSH has both "Kidney Failure, Chronic" and "Renal Insufficiency, Chronic"
 * for "chronic kidney disease"), and matching them all together would hand the
 * shared words to one entity, leaving the other's pill underlining nothing.
 */
function EntityPhrases({ text, entity }: EntityPhrasesProps) {
  if (!entity) return text
  return markPhrases(text, [entity]).map((run, index) =>
    run.entity ? (
      <span key={index} className="answer-entity">
        {run.text}
      </span>
    ) : (
      run.text
    ),
  )
}
