import { useLayoutEffect, useRef, useState } from 'react'
import EntityChip from '../components/EntityChip'
import type { EntityGroup } from './api'

interface Props {
  group: EntityGroup
  onOpen: () => void
}

/**
 * One saved group: its name, its entities as chips, and a count.
 *
 * Tiles are a fixed size so the grid stays even. Chips are measured after
 * layout, and any that would be cut by the bottom edge are hidden whole — a
 * half-drawn chip reads as a rendering bug — with "+N more" in the footer.
 */
export default function GroupTile({ group, onOpen }: Props) {
  const chipsRef = useRef<HTMLSpanElement>(null)
  const [fitting, setFitting] = useState(group.entities.length)
  const count = group.entities.length
  const hidden = count - fitting

  useLayoutEffect(() => {
    if (chipsRef.current) setFitting(countFittingChildren(chipsRef.current))
  }, [group.entities])

  return (
    <button type="button" className="group-tile" onClick={onOpen} title={`Edit ${group.name}`}>
      <span className="group-tile-name">{group.name}</span>
      <span className="group-tile-chips" ref={chipsRef}>
        {group.entities.map((entity, index) => (
          <span
            key={entity.entity_id}
            className={`group-tile-chip${index >= fitting ? ' group-tile-chip-hidden' : ''}`}
          >
            <EntityChip entity={entity} />
          </span>
        ))}
      </span>
      <span className="group-tile-count">
        {count} entit{count === 1 ? 'y' : 'ies'}
        {hidden > 0 && ` · +${hidden} more`}
      </span>
    </button>
  )
}

/**
 * How many leading children end above the container's bottom edge. Measured
 * with every child laid out, since hiding uses `visibility`, not `display`.
 */
function countFittingChildren(container: HTMLElement): number {
  const bottom = container.getBoundingClientRect().bottom
  const children = Array.from(container.children)
  const firstCut = children.findIndex((child) => child.getBoundingClientRect().bottom > bottom)
  return firstCut === -1 ? children.length : firstCut
}
