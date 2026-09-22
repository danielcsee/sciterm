# ui/src/chats

Client-side durable-conversation support for the authenticated `/chats` API.

`api.ts` starts a chat with its first user/assistant turn, appends later turns,
and converts a loaded server snapshot back into the existing `Message[]`
rendering model. Generated results, citations, answers, entity pills and
annotations are persisted by the server rather than uploaded from this client.

`ConversationsView.tsx` and `ConversationTile.tsx` render saved conversations
in a Smart Groups-style tile grid. Each tile's red bin opens
`DeleteChatModal.tsx`, which asks before permanently deleting the chat; its
annotations go with it. Opening a tile opens the chat in its own
tab at `/chat/<id>`, the way papers open, rather than on the homepage.

`useChatSessions.ts` keeps every open conversation's messages keyed by chat
id (plus a `draft` for the homepage's first question until the server names
it), so an answer streaming into one tab never lands in another. It also
loads a chat tab restored from storage or a shared link. Chats are named automatically from the first 20
characters of the first message. The root `App` remains responsible for state,
navigation, and network actions.

Dependencies: `authFetch`, the shared API/message types, and React.
