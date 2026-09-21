import type { Citation, SearchedPaper } from '../api'
import { sectionLabel } from '../sections'
import CitationMarker from './CitationMarker'
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
 * its cited paragraphs listed beneath. Each paragraph row is a citation
 * marker: hover shows the paragraph, click opens the paper at it.
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
            <ul className="citation-rows">
              {cited.map((citation) => (
                <li key={citation.chunk_id}>
                  <CitationMarker
                    citation={citation}
                    onOpen={onOpenCitation}
                    className="citation-row"
                  >
                    <span className="citation-row-number">[{citation.number}]</span>
                    <span className="citation-row-section">
                      {[
                        citation.section_type && sectionLabel(citation.section_type),
                        citation.selected_by,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                    <span className="citation-row-text">{citation.text}</span>
                  </CitationMarker>
                </li>
              ))}
            </ul>
          </PaperPreview>
        </li>
      ))}
    </ul>
  )
}
