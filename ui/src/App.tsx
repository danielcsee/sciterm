import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import {
  streamRagSearch,
  type Citation,
  type PaperDetail,
  type RagSearchResponse,
} from './api'
import { applyRagEvent, endRagStream, searchFailed } from './ragAnswer'
import { useAuth } from './auth'
import ChatWindow from './components/ChatWindow'
import CorpusView from './components/CorpusView'
import PaperTabs from './components/PaperTabs'
import PaperView from './components/PaperView'
import PaperExplorer, { type ReferenceTarget } from './components/PaperExplorer'
import {
  DefineTermButton,
  listAnnotations,
  useAnnotationUnderlines,
  useDefinition,
  type AnnotationDraft,
  type Highlight,
} from './define'
import { GroupsView } from './groups'
import { ConversationsView, useChatSessions, type SessionKey } from './chats'
import {
  CHAT,
  CONVERSATIONS,
  CORPUS,
  GROUPS,
  isTabView,
  loadTabs,
  pathToView,
  placeholderTab,
  sameView,
  saveTabs,
  TAB_FLASH_MS,
  tabKey,
  truncateTitle,
  viewKey,
  viewToPath,
  type OpenTab,
  type TabView,
  type View,
} from './navigation'
import type { Message, PaperFocus } from './types'
import {
  appendChatTurn,
  deleteSavedChat,
  listSavedChats,
  startChat,
  type SavedChatSummary,
} from './chats/api'

/**
 * Whether a click should be left to the browser: a modified or non-primary
 * click on a link means "open elsewhere", not "navigate here".
 */
function isNewTabClick(event: MouseEvent): boolean {
  return event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
}

function annotationFromHighlight(
  highlight: Highlight,
  activeChatId: number | null,
): AnnotationDraft | null {
  const common = {
    id: crypto.randomUUID(),
    phrase: highlight.phrase,
    surrounding_context: highlight.surroundingContext,
  }
  const selector = {
    source_key: highlight.source.sourceKey,
    quote_exact: highlight.selector.quoteExact,
    quote_prefix: highlight.selector.quotePrefix,
    quote_suffix: highlight.selector.quoteSuffix,
    start_offset: highlight.selector.startOffset,
    end_offset: highlight.selector.endOffset,
  }
  if (highlight.source.kind === 'chat') {
    if (activeChatId === null) return null
    return {
      ...common,
      source: {
        chat_id: activeChatId,
        chat_message_id: highlight.source.messageId,
        paper_id: null,
        paper_chunk_ordinal: null,
        ...selector,
      },
    }
  }
  return {
    ...common,
    source: {
      chat_id: null,
      chat_message_id: null,
      paper_id: highlight.source.paperId,
      paper_chunk_ordinal: highlight.source.chunkOrdinal,
      ...selector,
    },
  }
}

export default function App() {
  const { unlocked, promptForCode, requireAuth } = useAuth()
  const sessions = useChatSessions()
  const [savedChats, setSavedChats] = useState<SavedChatSummary[]>([])
  // The chat the homepage is showing, once its first message has created one.
  const [homeChatId, setHomeChatId] = useState<number | null>(null)
  const [chatOpening, setChatOpening] = useState(false)
  const [savedChatsLoading, setSavedChatsLoading] = useState(false)
  const [conversationListError, setConversationListError] = useState<string | null>(null)
  const [tabs, setTabs] = useState<OpenTab[]>(() => {
    // Tabs survive a reload; the URL still decides which one is showing. A
    // shared /paper/12 or /chat/3 link opens that tab too, with a placeholder
    // label until the paper or chat reports its real title.
    const stored = loadTabs()
    const initial = pathToView(window.location.pathname)
    if (!isTabView(initial)) return stored
    const key = viewKey(initial)
    return stored.some((tab) => tabKey(tab) === key)
      ? stored
      : [...stored, placeholderTab(initial)]
  })

  // Tabs briefly showing the selected styling after being opened in the
  // background, so the reader gets feedback for a tab they are not looking at.
  const [flashing, setFlashing] = useState<ReadonlySet<number>>(new Set())
  const flashTimers = useRef<Map<number, number>>(new Map())
  const [groupsFlashing, setGroupsFlashing] = useState(false)
  const groupsFlashTimer = useRef<number | null>(null)

  // Papers that 404ed this session. Their tab stays so the reader sees why,
  // but it must not come back after a reload.
  const [missing, setMissing] = useState<ReadonlySet<number>>(new Set())
  const [view, setView] = useState<View>(() => pathToView(window.location.pathname))
  // A cited paragraph to scroll to once its paper renders. Cleared as soon as
  // PaperView applies it, so returning to the tab later does not jump back.
  const [focus, setFocus] = useState<PaperFocus | null>(null)
  const focusNonce = useRef(0)
  // Which paper's references the side panel is showing, if any.
  const [referencesFor, setReferencesFor] = useState<ReferenceTarget | null>(null)
  const definition = useDefinition()
  const annotations = useMemo(
    () => definition.definitions.filter((entry) => !entry.hidden).map((entry) => entry.annotation),
    [definition.definitions],
  )
  useAnnotationUnderlines(annotations)
  // The conversation on screen, if any: a chat tab's, or the homepage's.
  const visibleChatId =
    view.kind === 'savedChat' ? view.chatId : view.kind === 'chat' ? homeChatId : null

  useEffect(() => {
    if (!unlocked) {
      setSavedChats([])
      setSavedChatsLoading(false)
      return
    }
    const controller = new AbortController()
    setSavedChatsLoading(true)
    setConversationListError(null)
    listSavedChats(controller.signal)
      .then((chats) => {
        setSavedChats(chats)
        setSavedChatsLoading(false)
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setConversationListError(
            error instanceof Error ? error.message : 'Could not list saved conversations.',
          )
          setSavedChatsLoading(false)
        }
      })
    return () => controller.abort()
  }, [unlocked])

  useEffect(() => {
    if (!unlocked) return
    const source = view.kind === 'paper'
      ? { paperId: view.paperId }
      : visibleChatId !== null
        ? { chatId: visibleChatId }
        : null
    if (source === null) return
    const controller = new AbortController()
    listAnnotations(source, controller.signal)
      .then(definition.hydrate)
      .catch(() => undefined)
    return () => controller.abort()
  }, [unlocked, view, visibleChatId, definition.hydrate])

  useEffect(() => {
    saveTabs(tabs.filter((tab) => tab.kind !== 'paper' || !missing.has(tab.paperId)))
  }, [tabs, missing])

  // Pending flashes must not fire into an unmounted tree.
  useEffect(() => {
    const timers = flashTimers.current
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer))
      timers.clear()
      if (groupsFlashTimer.current !== null) window.clearTimeout(groupsFlashTimer.current)
    }
  }, [])

  const flashGroupsTab = useCallback(() => {
    if (groupsFlashTimer.current !== null) window.clearTimeout(groupsFlashTimer.current)
    setGroupsFlashing(true)
    groupsFlashTimer.current = window.setTimeout(() => {
      groupsFlashTimer.current = null
      setGroupsFlashing(false)
    }, 1800)
  }, [])

  const flashTab = useCallback((paperId: number) => {
    const timers = flashTimers.current
    // Clicking the same icon again restarts the flash rather than letting the
    // first timer cut the second one short.
    const running = timers.get(paperId)
    if (running !== undefined) window.clearTimeout(running)

    setFlashing((prev) => (prev.has(paperId) ? prev : new Set(prev).add(paperId)))
    timers.set(
      paperId,
      window.setTimeout(() => {
        timers.delete(paperId)
        setFlashing((prev) => {
          if (!prev.has(paperId)) return prev
          const next = new Set(prev)
          next.delete(paperId)
          return next
        })
      }, TAB_FLASH_MS),
    )
  }, [])

  // Where the user has been, oldest first. Closing a paper tab pops back
  // through this, which a single "current view" could not answer.
  const historyRef = useRef<View[]>([])

  const navigate = useCallback((next: View, { push = true } = {}) => {
    setView((current) => {
      if (sameView(current, next)) return current
      historyRef.current = [...historyRef.current.slice(-19), current]
      if (push) {
        const path = viewToPath(next)
        if (path !== window.location.pathname) window.history.pushState({}, '', path)
      }
      return next
    })
  }, [])

  // Browser back/forward.
  useEffect(() => {
    const onPop = () => setView(pathToView(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  function addTab(tab: OpenTab) {
    const key = tabKey(tab)
    setTabs((prev) => (prev.some((open) => tabKey(open) === key) ? prev : [...prev, tab]))
  }

  function addPaperTab(paperId: number, title: string | null) {
    addTab({ kind: 'paper', paperId, title: title ?? `Paper ${paperId}` })
  }

  /** Give an open tab its real title once the paper or chat reports one. */
  const retitleTab = useCallback((view: TabView, title: string) => {
    const key = viewKey(view)
    setTabs((prev) => prev.map((tab) => (tabKey(tab) === key ? { ...tab, title } : tab)))
  }, [])

  function openPaper(paperId: number, title: string | null) {
    addPaperTab(paperId, title)
    navigate({ kind: 'paper', paperId })
  }

  function openCitation(citation: Citation, entityIds: number[], title: string | null) {
    focusNonce.current += 1
    setFocus({
      paperId: citation.paper_id,
      ordinal: citation.ordinal,
      entityIds,
      nonce: focusNonce.current,
    })
    openPaper(citation.paper_id, title)
  }

  const clearFocus = useCallback(() => setFocus(null), [])

  /**
   * Queue a paper up without leaving the current view — no navigate, so the
   * visit stack and the URL are untouched and the reader keeps their place.
   */
  function openPaperInBackground(paperId: number, title: string | null) {
    addPaperTab(paperId, title)
    flashTab(paperId)
  }

  /**
   * Define a highlighted phrase in the sidebar. The definition shows under the
   * search box, so a references panel covering it is closed first.
   */
  function defineHighlight(highlight: Highlight) {
    const annotation = annotationFromHighlight(highlight, visibleChatId)
    if (!annotation) return
    setReferencesFor(null)
    definition.request(annotation)
  }

  function closeTab(closing: TabView) {
    const remaining = tabs.filter((tab) => tabKey(tab) !== viewKey(closing))
    setTabs(remaining)

    // Closing a background tab must not move the user.
    if (!sameView(view, closing)) {
      historyRef.current = historyRef.current.filter((entry) => !sameView(entry, closing))
      return
    }

    // Fall back to the most recent view that still exists.
    const open = new Set(remaining.map(tabKey))
    const stack = historyRef.current.filter(
      (entry) => !isTabView(entry) || open.has(viewKey(entry)),
    )
    const previous = stack.pop() ?? CHAT
    historyRef.current = stack
    setView(previous)
    const path = viewToPath(previous)
    if (path !== window.location.pathname) window.history.pushState({}, '', path)
  }

  const handleMissing = useCallback((paperId: number) => {
    setMissing((prev) => (prev.has(paperId) ? prev : new Set(prev).add(paperId)))
  }, [])

  const handleLoaded = useCallback(
    (paper: PaperDetail) => {
      if (paper.title) retitleTab({ kind: 'paper', paperId: paper.paper_id }, paper.title)
    },
    [retitleTab],
  )

  // A chat tab restored from storage or a shared /chat/3 link has no messages
  // yet. A failed load is recorded rather than retried on every render;
  // reopening the chat from Conversations tries again.
  const shownChatId = view.kind === 'savedChat' ? view.chatId : null
  useEffect(() => {
    if (!unlocked || shownChatId === null) return
    if (sessions.messagesFor(shownChatId) || sessions.errorFor(shownChatId)) return
    sessions
      .load(shownChatId)
      .then((chat) => retitleTab({ kind: 'savedChat', chatId: chat.chat_id }, chat.title))
      .catch(() => undefined)
  }, [unlocked, shownChatId, sessions, retitleTab])

  /**
   * Ask the corpus. A `paper_analysis` query shows its citations first, then
   * streams its answer in beneath them; otherwise the answer is the routed
   * tool above the ranked papers.
   *
   * The assistant message is appended immediately in a pending state and then
   * filled in, so the question and a spinner appear at once instead of the
   * user staring at their own message alone.
   */
  async function handleSend(text: string, tabChatId: number | null) {
    const userId = crypto.randomUUID()
    const answerId = crypto.randomUUID()
    // A chat tab always has its id; the homepage has one after its first turn.
    const existingChatId = tabChatId ?? homeChatId
    let key: SessionKey = existingChatId ?? 'draft'
    sessions.append(key, [
      { id: userId, role: 'user', text },
      { id: answerId, role: 'assistant', text: 'Searching your corpus…', status: 'pending' },
    ])

    const update = (change: (message: Message) => Message) =>
      sessions.update(key, answerId, change)

    let response: RagSearchResponse | null = null
    try {
      const turn = {
        user_message_id: userId,
        assistant_message_id: answerId,
        content: text,
      }
      const chat = existingChatId === null
        ? await startChat(turn)
        : await appendChatTurn(existingChatId, turn)
      if (existingChatId === null) {
        sessions.adoptDraft(chat.chat_id)
        setHomeChatId(chat.chat_id)
        key = chat.chat_id
      }
      void listSavedChats().then(setSavedChats).catch(() => undefined)
      const chatId = chat.chat_id
      for await (const event of streamRagSearch(text, chatId, answerId)) {
        if (event.type === 'result') response = event.result
        const current = response
        update((message) => applyRagEvent(message, event, current))
      }
    } catch (err) {
      // Once the citations have arrived, keep them: only the answer failed.
      const current = response
      update((message) => (current ? endRagStream(message, current) : searchFailed(message, err)))
      return
    }
    const finished = response
    update((message) => endRagStream(message, finished))
  }

  /**
   * Fetch a saved chat unless it is already open — reloading one would
   * clobber an answer still streaming into it. Reports failure in the list.
   */
  async function loadChat(chatId: number): Promise<boolean> {
    if (sessions.messagesFor(chatId)) return true
    setChatOpening(true)
    setConversationListError(null)
    try {
      const chat = await sessions.load(chatId)
      definition.hydrate(chat.annotations)
      return true
    } catch (error) {
      setConversationListError(
        error instanceof Error ? error.message : 'Could not load that conversation.',
      )
      return false
    } finally {
      setChatOpening(false)
    }
  }

  /** Open a saved chat in its own tab, as papers are, at /chat/<id>. */
  async function openConversation(chatId: number) {
    if (!(await loadChat(chatId))) return
    const title = savedChats.find((chat) => chat.chat_id === chatId)?.title
    addTab({ kind: 'savedChat', chatId, title: title ?? `Chat ${chatId}` })
    navigate({ kind: 'savedChat', chatId })
  }

  async function deleteConversation(chatId: number) {
    await deleteSavedChat(chatId)
    setSavedChats((chats) => chats.filter((chat) => chat.chat_id !== chatId))
    sessions.forget(chatId)
    if (tabs.some((tab) => tab.kind === 'savedChat' && tab.chatId === chatId)) {
      closeTab({ kind: 'savedChat', chatId })
    }
    // The homepage's chat is gone, so its next message must start a new one.
    if (chatId === homeChatId) setHomeChatId(null)
    if (chatId === visibleChatId) definition.clear()
  }

  return (
    <div className="app">
      <header className="topbar">
        {/* A real link, so it can be opened in a new tab; a plain click stays
            in-app and returns to the chat without reloading it. */}
        <a
          className="brand"
          href={viewToPath(CHAT)}
          onClick={(event) => {
            if (isNewTabClick(event)) return
            event.preventDefault()
            navigate(CHAT)
          }}
        >
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">sciterm</span>
        </a>
        {/* The fixed tab sits outside PaperTabs so it never scrolls with them. */}
        <nav className="tabs">
          <button
            type="button"
            className={`tab${view.kind === 'corpus' ? ' tab-active' : ''}`}
            aria-current={view.kind === 'corpus' ? 'page' : undefined}
            onClick={() => navigate(CORPUS)}
          >
            My Corpus
          </button>
          <button
            type="button"
            className={`tab${view.kind === 'groups' ? ' tab-active' : ''}${
              groupsFlashing ? ' tab-flash' : ''
            }`}
            aria-current={view.kind === 'groups' ? 'page' : undefined}
            onClick={() => navigate(GROUPS)}
          >
            Smart Groups
          </button>
          <button
            type="button"
            className={`tab${view.kind === 'conversations' ? ' tab-active' : ''}`}
            aria-current={view.kind === 'conversations' ? 'page' : undefined}
            onClick={() => requireAuth(() => navigate(CONVERSATIONS))}
          >
            Conversations
          </button>
          {/* Only while locked. Once a code is accepted this disappears
              rather than turning into a "signed in" badge — there is no
              account to manage, so a persistent control would suggest one. */}
          {!unlocked && (
            <button type="button" className="tab tab-unlock" onClick={promptForCode}>
              Enter Access Code
            </button>
          )}
        </nav>
        <PaperTabs
          tabs={tabs}
          active={view}
          flashing={flashing}
          onSelect={navigate}
          onClose={closeTab}
        />
        <span className="brand-tagline">LLM for your chosen scientific literature</span>
      </header>

      <main className="layout">
        {/* The sidebar stays mounted across views: switching must not throw
            away a search, its scroll position, or a pending selection. */}
        {view.kind === 'paper' ? (
          <PaperView
            key={view.paperId}
            paperId={view.paperId}
            onViewReferences={(paperId, title) =>
              requireAuth(() => setReferencesFor({ paperId, title, kind: 'references' }))
            }
            onViewImportedReferences={(paperId, title) =>
              setReferencesFor({ paperId, title, kind: 'imported-references' })
            }
            onLoaded={handleLoaded}
            onMissing={handleMissing}
            focus={focus?.paperId === view.paperId ? focus : null}
            onFocusApplied={clearFocus}
          />
        ) : view.kind === 'groups' ? (
          <GroupsView
            onClose={() => navigate(CHAT)}
            onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
            onOpenPaperInBackground={(paperId, title) =>
              openPaperInBackground(paperId, truncateTitle(title, 200))
            }
          />
        ) : view.kind === 'conversations' ? (
          <ConversationsView
            conversations={savedChats}
            loading={savedChatsLoading}
            opening={chatOpening}
            error={conversationListError}
            onClose={() => navigate(CHAT)}
            onOpen={(chatId) => void openConversation(chatId)}
            onDelete={deleteConversation}
          />
        ) : view.kind === 'corpus' ? (
          <CorpusView
            onClose={() => navigate(CHAT)}
            onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
            onOpenPaperInBackground={(paperId, title) =>
              openPaperInBackground(paperId, truncateTitle(title, 200))
            }
          />
        ) : view.kind === 'savedChat' && !sessions.messagesFor(view.chatId) ? (
          <section className="chat" aria-label="Chat">
            <p
              className={`results-message${sessions.errorFor(view.chatId) ? ' results-error' : ''}`}
              role={sessions.errorFor(view.chatId) ? 'alert' : 'status'}
            >
              {!unlocked
                ? 'Enter the access code to open this conversation.'
                : sessions.errorFor(view.chatId) ?? 'Loading…'}
            </p>
          </section>
        ) : (
          <ChatWindow
            key={viewKey(view)}
            messages={sessions.messagesFor(visibleChatId ?? 'draft') ?? []}
            onSend={(text) => void handleSend(text, shownChatId)}
            onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
            onOpenCitation={(citation, entityIds, title) =>
              openCitation(citation, entityIds, truncateTitle(title, 200))
            }
            onSmartGroupCreated={flashGroupsTab}
          />
        )}
        <PaperExplorer
          referencesFor={referencesFor}
          onCloseReferences={() => setReferencesFor(null)}
          onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
          definitions={definition.definitions}
          onClearDefinition={definition.clear}
          onToggleDefinitionHidden={definition.toggleHidden}
          onDeleteDefinition={definition.remove}
        />
      </main>
      {/* Spends OpenAI tokens, so it is gated like the chat composer. */}
      <DefineTermButton
        onDefine={(highlight) => requireAuth(() => defineHighlight(highlight))}
      />
    </div>
  )
}
