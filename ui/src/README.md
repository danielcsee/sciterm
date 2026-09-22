# ui/src

Application source. The layout is flat: an entry point, a root component,
shared types, navigation, import tracking, the API client, plus
[`auth/`](auth), [`components/`](components), [`define/`](define) and
[`groups/`](groups), plus [`chats/`](chats) for saved conversations.

## Files

**`main.tsx`** — mounts `<App />` into `#root`, wrapped in `<AuthProvider>`,
and imports `styles.css`.

**`App.tsx`** — owns chat state, the open paper tabs and the visit stack.
Closing a paper tab pops that stack, skipping entries whose tab has since
closed: that is how "go back to where I was" works. `handleSend` reads the
`/corpus/rag_search` stream, folding each line into the reply with
`ragAnswer.ts`. A Smart Group saved from an answer briefly flashes the fixed
Smart Groups tab in the header.

**`ragAnswer.ts`** — pure message updates for that stream: the candidates, the
result, each answer piece, the finish, the answer's entities, and a connection
that dropped part-way.

**`entityPhrases.ts`** — splits answer text into plain runs and whole-word,
case-insensitive runs naming an entity, longest phrase first.
The sciterm logo is a link to `/`: a plain click returns to the chat in-app,
keeping the conversation; a modified click opens a new tab.

**`navigation.ts`** — `View`, the tab model, title truncation, the view↔URL
mapping, and `loadTabs`/`saveTabs`. The corpus and groups UI routes are
`/my-corpus` and `/my-groups`, clear of the `/corpus` and `/groups` API paths. Open tabs persist to `localStorage`; the active view
does not, since the URL carries it. Reads are validated and access guarded —
the store throws outright in a private window.

**`useImportStatus.ts`** — tracks an import and polls `/import/status` until
every paper is terminal. Polling, not push: the Celery worker is a separate
process from the API, so pushing would need a Redis pub/sub bridge, and
Postgres is already the durable source of truth. Fast ticks first, then backing
off, with a five-minute cap.

**`api.ts`** — typed access to the `/pb`, `/import` and `/corpus` routes,
mirroring the backend response models, so **changing one there means changing
this file too**. `streamRagSearch` yields the NDJSON lines of `rag_search`. Throws `ApiError`, which carries the HTTP status. Every call
goes through `authFetch` from [`auth/`](auth), which attaches the access token
and retries once through `/auth/refresh` on a 401.

**`types.ts`** — shared UI types. API payload types live in `api.ts`.

**`groups/`** — the Smart Groups page: saved entity groups, the type-ahead that
builds them, and their `/groups` API client. See its [README](groups).

**`chats/`** — the `/chats` client, snapshot↔`Message[]` conversion, save
modal, and Conversations tile view. Debug entity candidates are deliberately
excluded.

**`define/`** — "Define this term": a button beside highlighted chat or
paper text, and the definition it fetches into the sidebar. See its
[README](define).

**`auth/`** — the access-code gate: token store, `useAuth()`, and the modal.
The app loads whole for everyone; this decides which controls work. See its
[README](auth) before wiring a new gated control — the gate takes the *work*,
never the gated function itself.

**`styles.css`** — all styling, hand-written. No framework, no CSS modules.
