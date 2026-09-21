import { useEffect, useState } from 'react'
import { ApiError } from '../api'
import { fetchGroups, type EntityGroup } from './api'
import EditGroupModal from './EditGroupModal'
import GroupBuilder from './GroupBuilder'
import GroupTile from './GroupTile'

interface Props {
  onClose: () => void
}

/** The My Groups page: a builder for a new group, then every saved group as a tile. */
export default function GroupsView({ onClose }: Props) {
  const [groups, setGroups] = useState<EntityGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [building, setBuilding] = useState(false)
  const [editing, setEditing] = useState<EntityGroup | null>(null)

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

  return (
    <section className="groups" aria-label="My Groups">
      <header className="groups-header">
        <div>
          <h1 className="corpus-title">My Groups</h1>
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
            <GroupTile key={group.group_id} group={group} onOpen={() => setEditing(group)} />
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
