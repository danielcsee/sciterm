/**
 * Which view is on screen, which paper and chat tabs are open, and how to get
 * back.
 *
 * Closing a paper tab must return the user to whatever they were looking at
 * *before* that paper, which a single "current view" cannot answer. So this
 * keeps a visit stack and pops it, skipping entries whose tab has since
 * closed. Views also map to URLs, so a reload or a shared link lands somewhere
 * sensible.
 */

export type View =
  | { kind: 'chat' }
  | { kind: 'corpus' }
  | { kind: 'groups' }
  | { kind: 'conversations' }
  | { kind: 'paper'; paperId: number }
  /** A saved conversation opened in its own tab; the homepage is `chat`. */
  | { kind: 'savedChat'; chatId: number }

export interface PaperTab {
  kind: 'paper'
  paperId: number
  title: string
}

export interface ChatTab {
  kind: 'savedChat'
  chatId: number
  title: string
}

export type OpenTab = PaperTab | ChatTab

/** The views that live in a closable tab. */
export type TabView = Extract<View, { kind: 'paper' | 'savedChat' }>

export const CHAT: View = { kind: 'chat' }
export const CORPUS: View = { kind: 'corpus' }
export const GROUPS: View = { kind: 'groups' }
export const CONVERSATIONS: View = { kind: 'conversations' }

/** Tab labels are truncated to this many characters, then an ellipsis. */
export const TAB_TITLE_MAX = 20

/**
 * How long a newly backgrounded tab wears the selected styling.
 *
 * The icon opens a tab somewhere the reader is not looking, so without this
 * there is no feedback that anything happened.
 */
export const TAB_FLASH_MS = 500

export function sameView(a: View, b: View): boolean {
  return viewKey(a) === viewKey(b)
}

export function viewKey(view: View): string {
  if (view.kind === 'paper') return `paper:${view.paperId}`
  if (view.kind === 'savedChat') return `savedChat:${view.chatId}`
  return view.kind
}

export function isTabView(view: View): view is TabView {
  return view.kind === 'paper' || view.kind === 'savedChat'
}

/** The view a tab shows. */
export function tabView(tab: OpenTab): TabView {
  return tab.kind === 'paper'
    ? { kind: 'paper', paperId: tab.paperId }
    : { kind: 'savedChat', chatId: tab.chatId }
}

export function tabKey(tab: OpenTab): string {
  return viewKey(tabView(tab))
}

/** The placeholder label for a tab whose real title has not arrived yet. */
export function placeholderTab(view: TabView): OpenTab {
  return view.kind === 'paper'
    ? { kind: 'paper', paperId: view.paperId, title: `Paper ${view.paperId}` }
    : { kind: 'savedChat', chatId: view.chatId, title: `Chat ${view.chatId}` }
}

export function truncateTitle(title: string | null, max = TAB_TITLE_MAX): string {
  const text = (title ?? 'Untitled').trim()
  return text.length <= max ? text : `${text.slice(0, max).trimEnd()}…`
}

export function viewToPath(view: View): string {
  switch (view.kind) {
    case 'corpus':
      return '/my-corpus'
    case 'groups':
      return '/my-groups'
    case 'conversations':
      return '/conversations'
    case 'paper':
      return `/paper/${view.paperId}`
    case 'savedChat':
      return `/chat/${view.chatId}`
    default:
      return '/'
  }
}

function pathId(path: string, prefix: string): number | null {
  if (!path.startsWith(prefix)) return null
  const id = Number(path.slice(prefix.length))
  return Number.isInteger(id) && id > 0 ? id : null
}

export function pathToView(path: string): View {
  const paperId = pathId(path, '/paper/')
  if (paperId !== null) return { kind: 'paper', paperId }
  const chatId = pathId(path, '/chat/')
  if (chatId !== null) return { kind: 'savedChat', chatId }
  if (path === '/my-corpus') return CORPUS
  if (path === '/my-groups') return GROUPS
  return path === '/conversations' ? CONVERSATIONS : CHAT
}


// --- persistence -----------------------------------------------------------
//
// Open tabs survive a reload. The active view does not need storing: the URL
// already carries it, and it stays the authority so a shared link still wins.

const STORAGE_KEY = 'sciterm.openTabs.v1'

/**
 * The key this replaced, when the app was called litgraph.
 *
 * Renaming the key silently orphans whatever was under the old one — the tabs
 * are not read again, but the entry sits in every existing browser forever.
 * Removing it costs one call on load and leaves nothing behind. Dropping the
 * tabs themselves is the accepted price of the rename; they are a convenience,
 * and the URL still carries the active view.
 */
const LEGACY_STORAGE_KEY = 'litgraph.openTabs.v1'

function forgetLegacyTabs(): void {
  try {
    window.localStorage.removeItem(LEGACY_STORAGE_KEY)
  } catch {
    /* localStorage throws outright in private windows; nothing to clean up */
  }
}

/** Enough for any real session, and a bound on what a corrupt write can grow to. */
const MAX_STORED_TABS = 50
const MAX_STORED_TITLE = 300

function isPositiveId(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0
}

/**
 * A stored tab, or null. Entries written before chat tabs existed carry no
 * `kind` and are all papers.
 */
function parseStoredTab(value: unknown): OpenTab | null {
  if (typeof value !== 'object' || value === null) return null
  const tab = value as Record<string, unknown>
  if (typeof tab.title !== 'string') return null
  const title = tab.title.slice(0, MAX_STORED_TITLE)
  if (tab.kind === 'savedChat') {
    return isPositiveId(tab.chatId) ? { kind: 'savedChat', chatId: tab.chatId, title } : null
  }
  if (tab.kind !== undefined && tab.kind !== 'paper') return null
  return isPositiveId(tab.paperId) ? { kind: 'paper', paperId: tab.paperId, title } : null
}

/**
 * Read the stored tabs, or an empty list.
 *
 * Every failure is non-fatal. `localStorage` throws outright in some contexts
 * (private windows, blocked site data), and the stored value may predate a
 * change to this shape or have been edited by hand — none of which should stop
 * the app from starting.
 */
export function loadTabs(): OpenTab[] {
  forgetLegacyTabs()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    const seen = new Set<string>()
    const tabs: OpenTab[] = []
    for (const value of parsed) {
      const tab = parseStoredTab(value)
      if (tab === null || seen.has(tabKey(tab))) continue
      seen.add(tabKey(tab))
      tabs.push(tab)
      if (tabs.length === MAX_STORED_TABS) break
    }
    return tabs
  } catch {
    return []
  }
}

export function saveTabs(tabs: OpenTab[]): void {
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(
        tabs
          .slice(0, MAX_STORED_TABS)
          .map((tab) => ({ ...tab, title: tab.title.slice(0, MAX_STORED_TITLE) })),
      ),
    )
  } catch {
    // A full or unavailable store costs the user their tab list on reload,
    // which is not worth breaking the session over.
  }
}
