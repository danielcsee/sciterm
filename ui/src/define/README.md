# ui/src/define

"Define this term": highlight text in the chat or a paper, click the button
that appears beside it, and a plain-language definition from `POST /define`
shows in the sidebar under the Search PubTator box.

## Files

**`selection.ts`** — reads the highlight out of a `data-definable` region: the
phrase, its paragraph (none past 12 words), and a gutter spot for the button
right of the `data-definable-column`, or no button if the gutter is under 64px.
It also owns the CSS Custom Highlight that underlines defined phrases in yellow.

**`anchor.ts`** — re-finds a saved annotation's text: its source element by
the `data-annotation-*` attributes, then its offsets, falling back to the
quote and prefix if the offsets drifted.

**`useAnnotationUnderlines.ts`** — underlines every definition in the sidebar,
new or reloaded, re-anchoring whenever the page re-renders.

**`useHighlight.ts`** — re-reads the highlight on mouse release, keyboard
selection, scroll and resize; never mid-drag.

**`DefineTermButton.tsx`** — the fixed-position button. Its mousedown is
cancelled so clicking it keeps the highlight.

**`useDefinition.ts`** / **`api.ts`** — the definitions on screen, newest
first, the typed define call, and owner-scoped annotation reads. Requests carry
their source selector; the server saves it before defining. A reloaded
annotation whose definition never arrived shows as an error.

**`DefinitionPanel.tsx`** — the scrollable list of phrases with their
spinner, definition or error; a new one scrolls it back to the top.

## Wiring

`App` owns `useDefinition()` and `useAnnotationUnderlines()`, and renders the
button gated by `requireAuth`. `SearchPubTator` shows the list in place of its
results; a search clears it.
