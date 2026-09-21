import { useId, useState } from 'react'
import { entityLabel } from '../api'
import { suggestionToEntity, type EntitySuggestion, type GroupEntity } from './api'
import { useEntitySuggestions } from './useEntitySuggestions'

interface Props {
  /** Entities already chosen; they are left out of the dropdown. */
  excludeIds: ReadonlySet<number>
  onSelect: (entity: GroupEntity) => void
  placeholder?: string
  autoFocus?: boolean
}

/**
 * A text box that suggests corpus entities as you type — an ARIA combobox.
 *
 * Arrow keys move through the dropdown, Enter picks the highlighted entity (or
 * the first), Escape closes it. Picking clears the box and keeps focus, so the
 * next entity can be typed straight away.
 */
export default function EntityTypeahead({
  excludeIds,
  onSelect,
  placeholder = 'Type an entity — a gene, disease, chemical, species…',
  autoFocus = false,
}: Props) {
  const listId = useId()
  const [input, setInput] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const { suggestions, loading, error, searchable } = useEntitySuggestions(input)

  const options = suggestions.filter((suggestion) => !excludeIds.has(suggestion.entity_id))
  const showList = open && searchable
  const activeIndex = Math.min(active, Math.max(options.length - 1, 0))

  function choose(suggestion: EntitySuggestion) {
    onSelect(suggestionToEntity(suggestion))
    setInput('')
    setActive(0)
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    const step = keyStep(event.key)
    if (step !== 0 && options.length > 0) {
      event.preventDefault()
      // A closed list opens on the highlighted row rather than stepping past it.
      if (!showList) setOpen(true)
      else setActive((activeIndex + step + options.length) % options.length)
    } else if (event.key === 'Enter') {
      // Enter never submits a surrounding form from here: in this box it
      // means "pick", and an empty pick is a no-op.
      event.preventDefault()
      if (showList && options.length > 0) choose(options[activeIndex])
    } else if (event.key === 'Escape' && showList) {
      // Close the dropdown only; the enclosing dialog must not also close.
      event.preventDefault()
      event.stopPropagation()
      setOpen(false)
    }
  }

  return (
    <div className="typeahead">
      <input
        className="typeahead-input"
        type="text"
        role="combobox"
        aria-label="Add an entity"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          showList && options.length > 0 ? `${listId}-${activeIndex}` : undefined
        }
        value={input}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        autoFocus={autoFocus}
        onChange={(event) => {
          setInput(event.target.value)
          setOpen(true)
          setActive(0)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="typeahead-list" id={listId} role="listbox" aria-label="Matching entities">
          {options.map((suggestion, index) => (
            <li
              key={suggestion.entity_id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={`typeahead-option${index === activeIndex ? ' typeahead-option-active' : ''}`}
              // mousedown, not click: a click would blur the input first and
              // close the list before the pick lands.
              onMouseDown={(event) => {
                event.preventDefault()
                choose(suggestion)
              }}
              onMouseEnter={() => setActive(index)}
            >
              <SuggestionText suggestion={suggestion} />
            </li>
          ))}
          <TypeaheadStatus loading={loading} error={error} empty={options.length === 0} />
        </ul>
      )}
    </div>
  )
}

function SuggestionText({ suggestion }: { suggestion: EntitySuggestion }) {
  const label = entityLabel(suggestionToEntity(suggestion))
  const via = suggestion.matched_text.toLowerCase() !== label.toLowerCase()
  return (
    <>
      <span className="typeahead-name">{label}</span>
      <span className="typeahead-meta">
        {suggestion.entity_type}
        {via && ` · “${suggestion.matched_text}”`}
      </span>
    </>
  )
}

/** One non-selectable row saying why the list is empty, or what failed. */
function TypeaheadStatus({
  loading,
  error,
  empty,
}: {
  loading: boolean
  error: string | null
  empty: boolean
}) {
  if (!error && !empty) return null
  const text = error ?? (loading ? 'Searching…' : 'No matching entities in the corpus.')
  return (
    <li className="typeahead-status" role="presentation">
      {text}
    </li>
  )
}

function keyStep(key: string): number {
  if (key === 'ArrowDown') return 1
  if (key === 'ArrowUp') return -1
  return 0
}
