import { useEffect, useRef, useState, type RefObject } from 'react'
import type { EntityGroup, GroupEntity, SortOrder } from './api'
import GroupEntityEditor from './GroupEntityEditor'
import PaperSubgroupList from './PaperSubgroupList'
import SaveGroupModal from './SaveGroupModal'
import { useGroupPaperPages, type GroupPaperPages } from './useGroupPaperPages'

/** Distance from the bottom at which the next page starts loading, as in `CorpusView`. */
const SCROLL_MARGIN = '320px'

interface Props {
  group: EntityGroup
  onClose: () => void
  /** A new group saved from this page's edited entity list. */
  onGroupCreated: (group: EntityGroup) => void
  onOpenPaper: (paperId: number, title: string | null) => void
  onOpenPaperInBackground: (paperId: number, title: string | null) => void
}

/**
 * Every paper mentioning one of a group's entities, framed into subgroups of
 * similar topics. Replaces the groups page until closed. Subgroups arrive a
 * page at a time as the reader scrolls; the sort toggle refetches from page 1.
 *
 * The entities can be edited here without touching the saved group: each add
 * or remove reruns the search, and Save New Group (enabled once the list
 * differs from the group's) saves the edited list under a new name.
 */
export default function GroupPaperResults({
  group,
  onClose,
  onGroupCreated,
  onOpenPaper,
  onOpenPaperInBackground,
}: Props) {
  const [order, setOrder] = useState<SortOrder>('desc')
  const [entities, setEntities] = useState<GroupEntity[]>(group.entities)
  const [saving, setSaving] = useState(false)
  const entityIds = entities.map((entity) => entity.entity_id)
  const pages = useGroupPaperPages(entityIds, order)
  const canSave = entities.length > 0 && !sameEntities(entities, group.entities)
  const scrollRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  useLoadOnScroll(scrollRef, sentinelRef, pages.loadNext, pages.page)

  // A new order or entity list is a new list: start it from the top.
  const idsKey = entityIds.join(',')
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
  }, [order, idsKey])

  return (
    <section className="corpus" aria-label={`Papers in ${group.name}`}>
      <header className="corpus-header">
        <div className="group-results-heading">
          <h1 className="corpus-title">{group.name}</h1>
          <GroupEntityEditor
            groupName={group.name}
            summary={<ResultsSummary pages={pages} />}
            entities={entities}
            onRemove={(entityId) =>
              setEntities((prev) => prev.filter((entity) => entity.entity_id !== entityId))
            }
            onAdd={(entity) => setEntities((prev) => [...prev, entity])}
          />
          <SortToggle order={order} onChange={setOrder} />
        </div>
        <button className="corpus-close" type="button" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>

      <div className="group-results-body">
        <div className="group-results-gutter">
          <button
            type="button"
            className="group-button group-button-primary"
            onClick={() => setSaving(true)}
            disabled={!canSave}
            title={canSave ? undefined : 'Add or remove an entity to save a new group'}
          >
            Save New Group
          </button>
        </div>

        <div className="corpus-scroll" ref={scrollRef}>
          <PaperSubgroupList
            subgroups={pages.subgroups}
            entityCount={entities.length}
            onOpenPaper={onOpenPaper}
            onOpenPaperInBackground={onOpenPaperInBackground}
          />
          {/* Below the list, with real height — a zero-area target is unreliable. */}
          <div className="results-sentinel" ref={sentinelRef} aria-hidden="true" />
          <ResultsStatus pages={pages} empty={entities.length === 0} />
        </div>
      </div>

      {saving && (
        <SaveGroupModal
          entities={entities}
          onSaved={onGroupCreated}
          onClose={() => setSaving(false)}
        />
      )}
    </section>
  )
}

/**
 * Calls `onReach` whenever the sentinel comes within `SCROLL_MARGIN` of view.
 * Re-observes on each new `page`: an observer reports on subscribing, so a
 * page too short to fill the view still pulls in the next one.
 */
function useLoadOnScroll(
  rootRef: RefObject<HTMLDivElement | null>,
  sentinelRef: RefObject<HTMLDivElement | null>,
  onReach: () => void,
  page: number,
) {
  useEffect(() => {
    const sentinel = sentinelRef.current
    const root = rootRef.current
    if (!sentinel || !root) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) onReach()
      },
      { root, rootMargin: `0px 0px ${SCROLL_MARGIN} 0px` },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [rootRef, sentinelRef, onReach, page])
}

function ResultsSummary({ pages }: { pages: GroupPaperPages }) {
  if (pages.page === 0) return null
  const { totalPapers: papers, totalSubgroups: groups } = pages
  return (
    <p className="corpus-count">
      {papers.toLocaleString()} paper{papers === 1 ? '' : 's'} in {groups.toLocaleString()}{' '}
      subgroup{groups === 1 ? '' : 's'}
    </p>
  )
}

/** Flips subgroup size order; the label names the order now shown. */
function SortToggle({
  order,
  onChange,
}: {
  order: SortOrder
  onChange: (order: SortOrder) => void
}) {
  const descending = order === 'desc'
  return (
    <button
      type="button"
      className="sort-toggle"
      onClick={() => onChange(descending ? 'asc' : 'desc')}
      aria-label={`Sorted ${descending ? 'largest' : 'smallest'} subgroups first. Reverse order.`}
    >
      <span aria-hidden="true">{descending ? '↓' : '↑'}</span>{' '}
      {descending ? 'Largest subgroups first' : 'Smallest subgroups first'}
    </button>
  )
}

function ResultsStatus({ pages, empty }: { pages: GroupPaperPages; empty: boolean }) {
  if (empty) return <p className="results-message">Add an entity to search.</p>
  if (pages.error) return <p className="results-message results-error">{pages.error}</p>
  if (pages.loading) {
    return (
      <div className="results-loading" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        <span>Loading…</span>
      </div>
    )
  }
  if (pages.page > 0 && pages.subgroups.length === 0) {
    return <p className="results-message">No imported paper mentions these entities yet.</p>
  }
  return null
}

/** The same entities, in any order: order changes chips, not results. */
function sameEntities(a: GroupEntity[], b: GroupEntity[]): boolean {
  if (a.length !== b.length) return false
  const ids = new Set(b.map((entity) => entity.entity_id))
  return a.every((entity) => ids.has(entity.entity_id))
}
