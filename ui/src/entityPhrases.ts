import type { AnswerEntity } from './api'

/** A run of answer text: plain, or a phrase naming `entity`. */
export interface PhraseRun {
  text: string
  entity?: AnswerEntity
}

const WORD_CHAR = /[\p{L}\p{N}]/u

/**
 * Split `text` into plain runs and runs naming an entity.
 *
 * Every occurrence of every phrase is marked, ignoring case, but only as whole
 * words: "BRCA1" must not mark part of "BRCA12". Longer phrases win an
 * overlap, so "BRCA1 protein" is one run rather than "BRCA1" and a stray
 * " protein".
 */
export function markPhrases(text: string, entities: readonly AnswerEntity[]): PhraseRun[] {
  const ranges = phraseRanges(text, entities)
  const runs: PhraseRun[] = []
  let cursor = 0
  for (const range of ranges) {
    if (range.start > cursor) runs.push({ text: text.slice(cursor, range.start) })
    runs.push({ text: text.slice(range.start, range.end), entity: range.entity })
    cursor = range.end
  }
  if (cursor < text.length) runs.push({ text: text.slice(cursor) })
  return runs
}

interface Range {
  start: number
  end: number
  entity: AnswerEntity
}

/** Non-overlapping whole-word occurrences, longest phrase first, then sorted. */
function phraseRanges(text: string, entities: readonly AnswerEntity[]): Range[] {
  const phrases = entities
    .flatMap((entity) => entity.phrases.map((phrase) => ({ phrase, entity })))
    .filter(({ phrase }) => phrase.trim())
    .sort((a, b) => b.phrase.length - a.phrase.length)
  const taken: Range[] = []
  for (const { phrase, entity } of phrases) {
    for (const match of text.matchAll(new RegExp(escapeRegExp(phrase), 'giu'))) {
      const range = { start: match.index, end: match.index + match[0].length, entity }
      if (isWholeWord(text, range) && !taken.some((other) => overlaps(other, range))) {
        taken.push(range)
      }
    }
  }
  return taken.sort((a, b) => a.start - b.start)
}

function isWholeWord(text: string, range: Range): boolean {
  const before = text[range.start - 1]
  const after = text[range.end]
  return !(before && WORD_CHAR.test(before)) && !(after && WORD_CHAR.test(after))
}

function overlaps(a: Range, b: Range): boolean {
  return a.start < b.end && b.start < a.end
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
