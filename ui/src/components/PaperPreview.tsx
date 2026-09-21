import type { ReactNode } from 'react'
import type { SearchedPaper } from '../api'
import ExpandableText from './ExpandableText'
import PaperCard from './PaperCard'

interface Props {
  paper: SearchedPaper
  /** Detail for the card's id line, e.g. "2 terms · 14 mentions". */
  extra?: string
  onOpenPaper: (paperId: number, title: string | null) => void
  /** Evidence under the abstract: a matched passage, or citations. */
  children?: ReactNode
}

/**
 * One chat result: the clickable card, the abstract folded to a preview, then
 * whatever evidence the caller shows for it. Shared by search results and an
 * analysis's citations so the two read identically.
 */
export default function PaperPreview({ paper, extra, onOpenPaper, children }: Props) {
  return (
    <>
      <button
        type="button"
        className="chip chip-openable"
        onClick={() => onOpenPaper(paper.paper_id, paper.title)}
        title="Open paper"
      >
        <PaperCard
          title={paper.title}
          journal={paper.journal}
          year={paper.pub_year}
          pmid={paper.pmid}
          pmcid={paper.pmcid}
          extra={extra}
        />
      </button>
      {paper.abstract && (
        <blockquote className="rag-quote">
          <span className="rag-quote-section">ABSTRACT</span>
          <ExpandableText text={paper.abstract} />
        </blockquote>
      )}
      {children}
    </>
  )
}
