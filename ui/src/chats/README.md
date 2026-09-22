# ui/src/chats

Client-side durable-conversation support for the authenticated `/chats` API.

`api.ts` starts a chat with its first user/assistant turn, appends later turns,
and converts a loaded server snapshot back into the existing `Message[]`
rendering model. Generated results, citations, answers, entity pills and
annotations are persisted by the server rather than uploaded from this client.

`ConversationsView.tsx` and `ConversationTile.tsx` render saved conversations
in a Smart Groups-style tile grid. Opening a tile restores its snapshot into
the same main chat pane. Chats are named automatically from the first 20
characters of the first message. The root `App` remains responsible for state,
navigation, and network actions.

Dependencies: `authFetch`, the shared API/message types, and React.
