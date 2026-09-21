import type { SearchedPaper } from '../api'
import ExpandableText from './ExpandableText'
import PaperCard from './PaperCard'

interface Props {
  papers: SearchedPaper[]
  papersConsidered: number
  onOpenPaper: (paperId: number, title: string | null) => void
}

/** "2 terms · 14 mentions · most mentions of “BRCA1”" */
function paperSummary(paper: SearchedPaper): string {
  const parts = [
    `${paper.terms_matched} term${paper.terms_matched === 1 ? '' : 's'}`,
    `${paper.mentions} mention${paper.mentions === 1 ? '' : 's'}`,
    ...paper.selected_by,
  ]
  return parts.join(' · ')
}

/**
 * The papers behind an answer.
 *
 * There is no generated prose yet, so the "answer" is the selected papers
 * themselves. Each card previews the abstract, then the passage that got the
 * paper picked. Both arrive in full and are folded to a preview here.
 */
export default function RagResults({ papers, papersConsidered, onOpenPaper }: Props) {
  if (papers.length === 0) {
    return (
      <p className="rag-empty">
        No paper in your corpus mentions what you asked about. Import more
        papers, or try different wording.
      </p>
    )
  }

  return (
    <div className="rag">
      <p className="rag-lead">
        {papers.length} of {papersConsidered} matching paper
        {papersConsidered === 1 ? '' : 's'}:
      </p>
      <ul className="rag-list">
        {papers.map((paper) => (
          <li key={paper.paper_id}>
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
                extra={paperSummary(paper)}
              />
            </button>
            {paper.abstract && (
              <blockquote className="rag-quote">
                <span className="rag-quote-section">ABSTRACT</span>
                <ExpandableText text={paper.abstract} />
              </blockquote>
            )}
            {paper.chunks.length > 0 && (
              <blockquote className="rag-quote">
                <span className="rag-quote-section">
                  {['WHY IT WAS PICKED', paper.chunks[0].section_type]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
                <ExpandableText text={paper.chunks[0].text} />
              </blockquote>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
