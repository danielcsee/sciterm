# ui/src/define

"Define this term": highlight text in the chat or a paper, click the button
that appears beside it, and a plain-language definition from `POST /define`
shows in the sidebar under the Search PubTator box.

## Files

**`selection.ts`** — reads the highlight in a `data-definable` region: phrase,
paragraph (none past 12 words), and a button spot in the gutter right of the
`data-definable-column` (none under 64px). Owns the yellow CSS underline.

**`anchor.ts`** — re-finds a saved annotation's text: its source element by
the `data-annotation-*` attributes, then its offsets, falling back to the
quote and prefix if the offsets drifted.

**`useAnnotationUnderlines.ts`** — underlines every definition in the sidebar,
new or reloaded, re-anchoring whenever the page re-renders.

**`useHighlight.ts`** — re-reads the highlight on mouse release, keyboard
selection, scroll and resize.

**`DefineTermButton.tsx`** — the button; its mousedown is cancelled to keep
the highlight.

**`useDefinition.ts`** / **`api.ts`** — the definitions on screen, newest
first, the typed define call, and owner-scoped annotation reads and deletes.
Hiding one leaves it saved but drops it, and its underline, until a reload. The server
saves the selector before defining; a definition that never arrived shows as
an error.

**`DefinitionPanel.tsx`** — the scrollable list of phrases with their
spinner, definition or error; a new one scrolls to the top. Each card
has Hide and a red bin that permanently deletes it.

## Wiring

`App` owns both hooks and gates the button with `requireAuth`.
`SearchPubTator` shows the list in place of its results; a search clears it.
