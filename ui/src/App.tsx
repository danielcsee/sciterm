import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react'
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
  clearDefinitionUnderline,
  DefineTermButton,
  underlineDefinitionRange,
  useDefinition,
} from './define'
import { GroupsView } from './groups'
import {
  CHAT,
  CORPUS,
  GROUPS,
  loadTabs,
  pathToView,
  sameView,
  saveTabs,
  TAB_FLASH_MS,
  truncateTitle,
  viewToPath,
  type PaperTab,
  type View,
} from './navigation'
import type { Message, PaperFocus } from './types'
import {
  createSavedChat,
  isChatSaveable,
  listSavedChats,
  loadSavedChat,
  savedMessages,
  suggestedChatTitle,
  updateSavedChat,
  type SavedChatSummary,
} from './chats/api'

/**
 * Whether a click should be left to the browser: a modified or non-primary
 * click on a link means "open elsewhere", not "navigate here".
 */
function isNewTabClick(event: MouseEvent): boolean {
  return event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
}

export default function App() {
  const { unlocked, promptForCode, requireAuth } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [savedChats, setSavedChats] = useState<SavedChatSummary[]>([])
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [activeChatTitle, setActiveChatTitle] = useState<string | null>(null)
  const [chatSaveBusy, setChatSaveBusy] = useState(false)
  const [chatSaveError, setChatSaveError] = useState<string | null>(null)
  const [tabs, setTabs] = useState<PaperTab[]>(() => {
    // Tabs survive a reload; the URL still decides which one is showing. A
    // shared /paper/12 link opens that tab too, with a placeholder label until
    // PaperView reports the real title.
    const stored = loadTabs()
    const initial = pathToView(window.location.pathname)
    if (initial.kind !== 'paper') return stored
    return stored.some((tab) => tab.paperId === initial.paperId)
      ? stored
      : [...stored, { paperId: initial.paperId, title: `Paper ${initial.paperId}` }]
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

  useEffect(() => {
    if (!unlocked) {
      setSavedChats([])
      return
    }
    const controller = new AbortController()
    listSavedChats(controller.signal)
      .then(setSavedChats)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setChatSaveError(error instanceof Error ? error.message : 'Could not list saved chats.')
        }
      })
    return () => controller.abort()
  }, [unlocked])

  useEffect(() => {
    saveTabs(tabs.filter((tab) => !missing.has(tab.paperId)))
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

  function addTab(paperId: number, title: string | null) {
    setTabs((prev) =>
      prev.some((tab) => tab.paperId === paperId)
        ? prev
        : [...prev, { paperId, title: title ?? `Paper ${paperId}` }],
    )
  }

  function openPaper(paperId: number, title: string | null) {
    addTab(paperId, title)
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
    addTab(paperId, title)
    flashTab(paperId)
  }

  /**
   * Define a highlighted phrase in the sidebar. The definition shows under the
   * search box, so a references panel covering it is closed first.
   */
  function defineHighlight(phrase: string, surroundingContext: string | null, range: Range) {
    setReferencesFor(null)
    underlineDefinitionRange(range)
    definition.request(phrase, surroundingContext)
  }

  function clearDefinition() {
    clearDefinitionUnderline()
    definition.clear()
  }

  function closePaper(paperId: number) {
    const remaining = tabs.filter((tab) => tab.paperId !== paperId)
    setTabs(remaining)

    // Closing a background tab must not move the user.
    if (view.kind !== 'paper' || view.paperId !== paperId) {
      historyRef.current = historyRef.current.filter(
        (entry) => entry.kind !== 'paper' || entry.paperId !== paperId,
      )
      return
    }

    // Fall back to the most recent view that still exists.
    const open = new Set(remaining.map((tab) => tab.paperId))
    const stack = historyRef.current.filter(
      (entry) => entry.kind !== 'paper' || open.has(entry.paperId),
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

  const handleLoaded = useCallback((paper: PaperDetail) => {
    setTabs((prev) =>
      prev.map((tab) =>
        tab.paperId === paper.paper_id && paper.title
          ? { ...tab, title: paper.title }
          : tab,
      ),
    )
  }, [])

  /**
   * Ask the corpus. A `paper_analysis` query shows its citations first, then
   * streams its answer in beneath them; otherwise the answer is the routed
   * tool above the ranked papers.
   *
   * The assistant message is appended immediately in a pending state and then
   * filled in, so the question and a spinner appear at once instead of the
   * user staring at their own message alone.
   */
  async function handleSend(text: string) {
    const answerId = crypto.randomUUID()
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', text },
      { id: answerId, role: 'assistant', text: 'Searching your corpus…', status: 'pending' },
    ])

    const update = (change: (message: Message) => Message) =>
      setMessages((prev) =>
        prev.map((message) => (message.id === answerId ? change(message) : message)),
      )

    let response: RagSearchResponse | null = null
    try {
      for await (const event of streamRagSearch(text)) {
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

  async function loadChat(chatId: number) {
    setChatSaveBusy(true)
    setChatSaveError(null)
    try {
      const chat = await loadSavedChat(chatId)
      setMessages(savedMessages(chat))
      setActiveChatId(chat.chat_id)
      setActiveChatTitle(chat.title)
    } catch (error) {
      setChatSaveError(error instanceof Error ? error.message : 'Could not load that chat.')
    } finally {
      setChatSaveBusy(false)
    }
  }

  async function saveChat() {
    if (!isChatSaveable(messages)) return
    setChatSaveBusy(true)
    setChatSaveError(null)
    const title = activeChatTitle ?? suggestedChatTitle(messages)
    try {
      const chat =
        activeChatId === null
          ? await createSavedChat(title, messages)
          : await updateSavedChat(activeChatId, title, messages)
      setActiveChatId(chat.chat_id)
      setActiveChatTitle(chat.title)
      setSavedChats(await listSavedChats())
    } catch (error) {
      setChatSaveError(error instanceof Error ? error.message : 'Could not save this chat.')
    } finally {
      setChatSaveBusy(false)
    }
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
          onSelect={(paperId) => navigate({ kind: 'paper', paperId })}
          onClose={closePaper}
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
        ) : view.kind === 'corpus' ? (
          <CorpusView
            onClose={() => navigate(CHAT)}
            onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
            onOpenPaperInBackground={(paperId, title) =>
              openPaperInBackground(paperId, truncateTitle(title, 200))
            }
          />
        ) : (
          <ChatWindow
            messages={messages}
            onSend={(text) => void handleSend(text)}
            onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
            onOpenCitation={(citation, entityIds, title) =>
              openCitation(citation, entityIds, truncateTitle(title, 200))
            }
            onSmartGroupCreated={flashGroupsTab}
            savedChats={savedChats}
            activeChatId={activeChatId}
            chatSaveBusy={chatSaveBusy}
            chatSaveError={chatSaveError}
            canSaveChat={unlocked && isChatSaveable(messages)}
            onLoadChat={(chatId) => void loadChat(chatId)}
            onSaveChat={() => void saveChat()}
          />
        )}
        <PaperExplorer
          referencesFor={referencesFor}
          onCloseReferences={() => setReferencesFor(null)}
          onOpenPaper={(paperId, title) => openPaper(paperId, truncateTitle(title, 200))}
          definitions={definition.definitions}
          onClearDefinition={clearDefinition}
        />
      </main>
      {/* Spends OpenAI tokens, so it is gated like the chat composer. */}
      <DefineTermButton
        onDefine={(phrase, context, range) =>
          requireAuth(() => defineHighlight(phrase, context, range))
        }
      />
    </div>
  )
}
