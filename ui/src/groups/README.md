# ui/src/groups

The Smart Groups page (`/my-groups`): shared, named sets of corpus entities.

## Files

**`GroupsView.tsx`** — the page. "+ New Group" opens `GroupBuilder`; saved
groups follow as `GroupTile`s, newest first. A tile click or Search opens
`GroupPaperResults`; Edit opens `EditGroupModal`.

**`GroupPaperResults.tsx`** — the group's papers, paged on scroll by
`useGroupPaperPages.ts`. The count is followed by the group's
entities as `EntityChip`s. The toggle reverses subgroup size order and
refetches; ✕ returns. `PaperSubgroupList.tsx` frames subgroups of 2+.

**`GroupBuilder.tsx`** — type-ahead with Save Group beside it, chosen entities
as removable `EntityChip`s beneath. Save is disabled while empty and opens
`SaveGroupModal` for the name.

**`EditGroupModal.tsx`** — rename, add/remove entities, or delete (the button
asks once more in place). Nothing is written until Save.

**`GroupTile.tsx`** — fixed 192×164 tiles; a `<div>`, since its
buttons cannot nest in a button. Search (with the
outgoing-arrow icon) sits top right, Edit bottom right. Chips that would be cut off are measured and hidden whole; the footer says "+N more".

**`EntityTypeahead.tsx`** / **`useEntitySuggestions.ts`** — an ARIA combobox
over `/entities/suggest`: 250 ms debounce, three characters minimum, and each
keystroke aborts the request in flight.

**`useModalDialog.ts`** — native `<dialog>` handling shared by both modals,
as in `AccessCodeModal`, whose `code-*` classes they reuse for a matching look.

**`api.ts`** — the `/groups`, `/groups/{id}/papers`, and `/entities/suggest`
client, mirroring `api/groups/schemas.py` and `api/group_search/schemas.py`.

Duplicate names (compared ignoring case) come back as a 409 and show under
the name field.

## Dependencies

React, `../api` (`ApiError`, `entityLabel`), `../auth` (`authFetch`), and
`../components` (`EntityChip`, `PaperCard`, `OpenInTabButton`).
