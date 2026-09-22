# ui/src/define

"Define this term": highlight text in the chat or a paper, click the button
that appears beside it, and a plain-language definition from `POST /define`
shows in the sidebar under the Search PubTator box.

## Files

**`selection.ts`** — reads the highlight out of the DOM: the phrase, the
paragraph around it, and where the button goes. Only text inside an element
marked `data-definable` counts; the text column inside it is marked
`data-definable-column`, and the button sits in the gutter to that column's
right, level with the first highlighted line. With no gutter at least 64px
wide, no button is shown rather than one covering text. It also registers the
selected range with the CSS Custom Highlight API so the requested phrase keeps
a yellow underline while its definition is open.

Highlights over 12 words are sent with `surrounding_context: null`. Otherwise
the context is the block (`p`, `li`, heading…) the highlight starts in —
split at blank lines, since a chat answer is one pre-wrap `<p>` — plus the one
it ends in, if different.

**`useHighlight.ts`** — re-reads the highlight on mouse release, keyboard
selection, scroll and resize; never mid-drag.

**`DefineTermButton.tsx`** — the fixed-position button. Its mousedown is
cancelled so clicking it keeps the highlight.

**`useDefinition.ts`** / **`api.ts`** — the definition on screen, and the
typed call. A new request aborts the last.

**`DefinitionPanel.tsx`** — the phrase, then a spinner, definition or error.

## Wiring

`App` owns `useDefinition()` and renders the button, gated by `requireAuth`
(it spends OpenAI tokens). `SearchPubTator` shows the panel in place of its
results, hidden rather than unmounted, and clears it when a search starts.
