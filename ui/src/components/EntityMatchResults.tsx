import type { EntityMatch, EntityMatchGroup, EntityStrategyGroup } from '../api'

type Group = EntityMatchGroup | EntityStrategyGroup
type Match = EntityMatch & { query_fragment?: string }

interface Props {
  groups: Group[]
}

const extractionLabels = {
  noun_phrase: 'noun chunking',
  three_gram: '3-gram',
} as const

const sourceLabels = {
  entity_name: 'entity names',
  mention_surface_text: 'mention text',
} as const

/** Raw groups belong to one fragment; filtered groups pool every fragment. */
function groupFragment(group: Group): string | undefined {
  return 'query_fragment' in group ? group.query_fragment : undefined
}

function groupKey(group: Group): string {
  return `${group.extraction_method}:${group.match_method}:${group.source}:${groupFragment(group) ?? ''}`
}

function matchDetail(match: Match): string {
  const matched = match.matched_text !== match.name ? ` · matched “${match.matched_text}”` : ''
  const via = match.query_fragment ? ` · from “${match.query_fragment}”` : ''
  return `${match.identifier} · ${match.entity_type} · ${match.score.toFixed(3)}${matched}${via}`
}

/** Experimental entity candidates, grouped so every discovery path is visible. */
export default function EntityMatchResults({ groups }: Props) {
  const matched = groups.filter((group) => group.matches.length > 0)
  if (matched.length === 0) {
    return <p className="entity-match-empty">No entity candidates passed their cutoffs.</p>
  }

  return (
    <section className="entity-matches" aria-label="Entity matching experiment">
      {matched.map((group) => {
        const fragment = groupFragment(group)
        return (
          <div className="entity-match-group" key={groupKey(group)}>
            <p className="entity-match-path">
              {fragment !== undefined && `“${fragment}” · `}
              {extractionLabels[group.extraction_method]} with {group.match_method}s ·{' '}
              {sourceLabels[group.source]}
            </p>
            <ol>
              {group.matches.map((match: Match) => (
                <li key={`${match.entity_id}:${match.matched_text}`}>
                  <span className="entity-match-name">{match.name ?? match.matched_text}</span>{' '}
                  <span className="entity-match-meta">{matchDetail(match)}</span>
                </li>
              ))}
            </ol>
          </div>
        )
      })}
    </section>
  )
}
