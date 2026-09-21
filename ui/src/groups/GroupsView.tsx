import { useEffect, useState } from 'react'
import { ApiError } from '../api'
import { fetchGroups, type EntityGroup } from './api'
import EditGroupModal from './EditGroupModal'
import GroupBuilder from './GroupBuilder'
import GroupPaperResults from './GroupPaperResults'
import GroupTile from './GroupTile'

interface Props {
  onClose: () => void
  onOpenPaper: (paperId: number, title: string | null) => void
  onOpenPaperInBackground: (paperId: number, title: string | null) => void
}

/**
 * The Smart Groups page: a builder for a new group, then every saved group as a
 * tile. Searching a group swaps the page for that group's paper results until
 * they are closed; the groups stay loaded underneath.
 */
export default function GroupsView({ onClose, onOpenPaper, onOpenPaperInBackground }: Props) {
  const [groups, setGroups] = useState<EntityGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [building, setBuilding] = useState(false)
  const [editing, setEditing] = useState<EntityGroup | null>(null)
  const [searching, setSearching] = useState<EntityGroup | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchGroups(controller.signal)
      .then((loaded) => {
        setGroups(loaded)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
        setLoading(false)
      })
    return () => controller.abort()
  }, [])

  if (searching) {
    return (
      <GroupPaperResults
        // A saved group is a fresh page: its own entities, Save greyed again.
        key={searching.group_id}
        group={searching}
        onClose={() => setSearching(null)}
        onGroupCreated={(group) => {
          setGroups((prev) => [group, ...prev])
          setSearching(group)
        }}
        onOpenPaper={onOpenPaper}
        onOpenPaperInBackground={onOpenPaperInBackground}
      />
    )
  }

  return (
    <section className="groups" aria-label="Smart Groups">
      <header className="groups-header">
        <div>
          <h1 className="corpus-title">Smart Groups</h1>
          {groups.length > 0 && (
            <p className="corpus-count">
              {groups.length} group{groups.length === 1 ? '' : 's'}
            </p>
          )}
        </div>
        <button className="corpus-close" type="button" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>

      <div className="groups-scroll">
        {building ? (
          <GroupBuilder
            onSaved={(group) => {
              setGroups((prev) => [group, ...prev])
              setBuilding(false)
            }}
            onCancel={() => setBuilding(false)}
          />
        ) : (
          <button type="button" className="group-new" onClick={() => setBuilding(true)}>
            <span className="group-new-plus" aria-hidden="true">+</span> New Group
          </button>
        )}

        <GroupsStatus loading={loading} error={error} empty={groups.length === 0} />
        <div className="group-grid">
          {groups.map((group) => (
            <GroupTile
              key={group.group_id}
              group={group}
              onSearch={() => setSearching(group)}
              onEdit={() => setEditing(group)}
            />
          ))}
        </div>
      </div>

      {editing && (
        <EditGroupModal
          group={editing}
          onSaved={(saved) => {
            setGroups((prev) => replaceGroup(prev, saved))
            setEditing(null)
          }}
          onDeleted={(groupId) => {
            setGroups((prev) => prev.filter((group) => group.group_id !== groupId))
            setEditing(null)
          }}
          onClose={() => setEditing(null)}
        />
      )}
    </section>
  )
}

function GroupsStatus({
  loading,
  error,
  empty,
}: {
  loading: boolean
  error: string | null
  empty: boolean
}) {
  if (error) return <p className="results-message results-error">{error}</p>
  if (loading) return <p className="results-message">Loading…</p>
  if (empty) {
    return (
      <p className="results-message">
        No groups yet. Press New Group, add some entities, and save.
      </p>
    )
  }
  return null
}

function replaceGroup(groups: EntityGroup[], saved: EntityGroup): EntityGroup[] {
  return groups.map((group) => (group.group_id === saved.group_id ? saved : group))
}
