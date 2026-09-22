# ui/src/chats

Client-side saved-chat support for the authenticated `/chats` API.

`api.ts` owns the wire types and converts between the backend snapshot and the
existing `Message[]` rendering model. The conversion deliberately includes
queries, assistant output, result papers, citations and answer entity pills,
but never copies the experimental entity-match/debug fields.

`SavedChatControls.tsx` is the compact chat toolbar: it selects an existing
snapshot and saves or updates the conversation currently in memory. The root
`App` remains responsible for state and network actions so loading a snapshot
uses the same `messages` state as a live streamed conversation.

Dependencies: `authFetch`, the shared API/message types, and React.
