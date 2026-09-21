import OpenInTabButton from '../components/OpenInTabButton'
import PaperCard from '../components/PaperCard'
import type { GroupPaper, PaperSubgroup } from './api'

interface Props {
  subgroups: PaperSubgroup[]
  /** Entities in the group, for the "2 of 4 entities" line on each card. */
  entityCount: number
  onOpenPaper: (paperId: number, title: string | null) => void
  onOpenPaperInBackground: (paperId: number, title: string | null) => void
}

/**
 * Subgroups in server order. A subgroup of two or more papers is framed, since
 * its papers discuss similar topics; a paper alone stands unframed.
 */
export default function PaperSubgroupList({
  subgroups,
  entityCount,
  onOpenPaper,
  onOpenPaperInBackground,
}: Props) {
  return (
    <ul className="subgroup-list">
      {subgroups.map((group) => (
        <li
          key={group.papers[0].paper_id}
          className={group.size > 1 ? 'subgroup subgroup-framed' : 'subgroup'}
        >
          {group.size > 1 && <p className="subgroup-label">{group.size} similar papers</p>}
          <ul className="subgroup-papers">
            {group.papers.map((paper) => (
              <GroupPaperItem
                key={paper.paper_id}
                paper={paper}
                entityCount={entityCount}
                onOpenPaper={onOpenPaper}
                onOpenPaperInBackground={onOpenPaperInBackground}
              />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

/** A corpus-style card; the card and its tab action are siblings, as in `CorpusView`. */
function GroupPaperItem({
  paper,
  entityCount,
  onOpenPaper,
  onOpenPaperInBackground,
}: {
  paper: GroupPaper
  entityCount: number
  onOpenPaper: Props['onOpenPaper']
  onOpenPaperInBackground: Props['onOpenPaperInBackground']
}) {
  return (
    <li className="card-slot">
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
          snippet={paper.snippet}
          pmid={paper.pmid}
          pmcid={paper.pmcid}
          extra={`${paper.match_count} of ${entityCount} entit${entityCount === 1 ? 'y' : 'ies'}`}
        />
      </button>
      <OpenInTabButton
        label={paper.title ?? `paper ${paper.paper_id}`}
        onClick={() => onOpenPaperInBackground(paper.paper_id, paper.title)}
      />
    </li>
  )
}
