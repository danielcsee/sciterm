# ui/src/chats

Client-side saved-conversation support for the authenticated `/chats` API.

`api.ts` owns the wire types and converts between the backend snapshot and the
existing `Message[]` rendering model. The conversion deliberately includes
queries, assistant output, result papers, citations and answer entity pills,
but never copies the experimental entity-match/debug fields.

`SaveConversationModal.tsx` names the current chat snapshot before it is saved;
the suggested name is the first 20 characters of the first user message.
`ConversationsView.tsx` and `ConversationTile.tsx` render saved conversations
in a Smart Groups-style tile grid. Opening a tile restores its snapshot into
the same main chat pane. The root `App` remains responsible for state,
navigation, and network actions.

Dependencies: `authFetch`, the shared API/message types, and React.
