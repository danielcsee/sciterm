import type { Citation, SearchedPaper } from '../api'
import { sectionLabel } from '../sections'
import CitationMarker from './CitationMarker'
import ExpandableText from './ExpandableText'
import PaperPreview from './PaperPreview'

interface Props {
  citations: Citation[]
  papers: SearchedPaper[]
  onOpenPaper: (paperId: number, title: string | null) => void
  onOpenCitation: (citation: Citation) => void
}

interface CitedPaper {
  paper: SearchedPaper
  citations: Citation[]
}

/** Citations grouped under their paper, in the order the server numbered them. */
export function groupByPaper(citations: Citation[], papers: SearchedPaper[]): CitedPaper[] {
  const byId = new Map(papers.map((paper) => [paper.paper_id, paper]))
  const groups = new Map<number, CitedPaper>()
  for (const citation of citations) {
    const paper = byId.get(citation.paper_id)
    if (!paper) continue
    const group = groups.get(paper.paper_id)
    if (group) group.citations.push(citation)
    else groups.set(paper.paper_id, { paper, citations: [citation] })
  }
  return Array.from(groups.values())
}

/**
 * The paragraphs an answer was grounded in, one paper preview per paper with
 * its cited paragraphs quoted beneath, folded to 300 characters like the
 * search previews. Each quote's heading is a citation marker: hover shows the
 * whole paragraph, click opens the paper at it.
 */
export default function CitationList({ citations, papers, onOpenPaper, onOpenCitation }: Props) {
  return (
    <ul className="rag-list citation-list">
      {groupByPaper(citations, papers).map(({ paper, citations: cited }) => (
        <li key={paper.paper_id}>
          <PaperPreview
            paper={paper}
            extra={`${cited.length} cited paragraph${cited.length === 1 ? '' : 's'}`}
            onOpenPaper={onOpenPaper}
          >
            {cited.map((citation) => (
              <blockquote key={citation.chunk_id} className="rag-quote">
                <CitationMarker
                  citation={citation}
                  onOpen={onOpenCitation}
                  className="citation-heading"
                >
                  {[
                    `[${citation.number}]`,
                    citation.section_type && sectionLabel(citation.section_type).toUpperCase(),
                    citation.selected_by.toUpperCase(),
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </CitationMarker>
                <ExpandableText text={citation.text} />
              </blockquote>
            ))}
          </PaperPreview>
        </li>
      ))}
    </ul>
  )
}
