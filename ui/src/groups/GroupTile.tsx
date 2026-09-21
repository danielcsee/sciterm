import { useLayoutEffect, useRef, useState, type MouseEvent } from 'react'
import EntityChip from '../components/EntityChip'
import OutgoingArrowIcon from '../components/OutgoingArrowIcon'
import type { EntityGroup } from './api'

interface Props {
  group: EntityGroup
  /** Searches for the group's papers: a click anywhere on the tile, or Search. */
  onSearch: () => void
  onEdit: () => void
}

/**
 * One saved group: its name, its entities as chips, and a count.
 *
 * The tile is a clickable `<div>`, not a button, because it holds two buttons
 * and a button inside a button is invalid. Search is the keyboard route to
 * what a click on the tile does, so the tile needs no tab stop of its own.
 *
 * Tiles are a fixed size so the grid stays even. Chips are measured after
 * layout, and any that would be cut by the bottom edge are hidden whole — a
 * half-drawn chip reads as a rendering bug — with "+N more" in the footer.
 */
export default function GroupTile({ group, onSearch, onEdit }: Props) {
  const chipsRef = useRef<HTMLSpanElement>(null)
  const [fitting, setFitting] = useState(group.entities.length)
  const count = group.entities.length
  const hidden = count - fitting

  useLayoutEffect(() => {
    if (chipsRef.current) setFitting(countFittingChildren(chipsRef.current))
  }, [group.entities])

  return (
    <div className="group-tile" onClick={onSearch} title={`Search papers in ${group.name}`}>
      <span className="group-tile-head">
        <span className="group-tile-name">{group.name}</span>
        <button
          type="button"
          className="group-tile-search"
          onClick={(event) => runAlone(event, onSearch)}
          aria-label={`Search papers in ${group.name}`}
          title={`Search papers in ${group.name}`}
        >
          Search
          <OutgoingArrowIcon />
        </button>
      </span>
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
      <span className="group-tile-foot">
        <span className="group-tile-count">
          {count} entit{count === 1 ? 'y' : 'ies'}
          {hidden > 0 && ` · +${hidden} more`}
        </span>
        <button
          type="button"
          className="group-tile-edit"
          onClick={(event) => runAlone(event, onEdit)}
          aria-label={`Edit ${group.name}`}
          title={`Edit ${group.name}`}
        >
          Edit
        </button>
      </span>
    </div>
  )
}

/** Runs a button's action without the click also reaching the tile beneath. */
function runAlone(event: MouseEvent, action: () => void) {
  event.stopPropagation()
  action()
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
