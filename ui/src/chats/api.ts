import { authFetch } from '../auth/session'
import type { AnswerEntity, Citation, PaperAnalysisResult, SearchedPaper } from '../api'
import type { Message, MessageStatus, Role } from '../types'

export interface SavedChatSummary {
  chat_id: number
  title: string
  message_count: number
  preview: string
  created_at: string
  updated_at: string
}

interface SavedCitation extends Citation {
  paper_pmid: number | null
  paper_title: string | null
}

interface SavedEntityPill extends Omit<AnswerEntity, 'entity_id'> {
  entity_id: number | null
}

interface SavedChatMessage {
  id: string
  role: Role
  content: string
  status: Exclude<MessageStatus, 'pending'>
  fallback_text: string | null
  response_kind: 'paper_search' | 'paper_analysis' | 'no_match' | null
  result_papers: SearchedPaper[]
  papers_considered: number
  analysis_entity_ids: number[]
  analysis_duplicates_rejected: number
  analysis_model: string | null
  analysis_error: string | null
  citations: SavedCitation[]
  entity_pills: SavedEntityPill[]
}

interface SaveChatBody {
  title: string
  messages: SavedChatMessage[]
}

export interface SavedChat extends SaveChatBody {
  chat_id: number
  created_at: string
  updated_at: string
}

export async function listSavedChats(signal?: AbortSignal): Promise<SavedChatSummary[]> {
  const response = await authFetch('/chats', { signal })
  if (!response.ok) throw new Error(await errorDetail(response, 'Could not list saved chats.'))
  const body = (await response.json()) as { chats: SavedChatSummary[] }
  return body.chats
}

export async function loadSavedChat(chatId: number, signal?: AbortSignal): Promise<SavedChat> {
  const response = await authFetch(`/chats/${chatId}`, { signal })
  if (!response.ok) throw new Error(await errorDetail(response, 'Could not load that chat.'))
  return (await response.json()) as SavedChat
}

export async function createSavedChat(
  title: string,
  messages: Message[],
): Promise<SavedChat> {
  return writeChat('/chats', 'POST', title, messages)
}

export async function updateSavedChat(
  chatId: number,
  title: string,
  messages: Message[],
): Promise<SavedChat> {
  return writeChat(`/chats/${chatId}`, 'PUT', title, messages)
}

export function savedMessages(chat: SavedChat): Message[] {
  return chat.messages.map(fromSavedMessage)
}

export function suggestedChatTitle(messages: readonly Message[]): string {
  const query = messages.find((message) => message.role === 'user')?.text.trim()
  if (!query) return 'Saved conversation'
  return query.slice(0, 20)
}

export function isChatSaveable(messages: readonly Message[]): boolean {
  return (
    messages.length > 0 &&
    messages[0].role === 'user' &&
    messages.every((message) => message.status !== 'pending')
  )
}

async function writeChat(
  url: string,
  method: 'POST' | 'PUT',
  title: string,
  messages: Message[],
): Promise<SavedChat> {
  const body: SaveChatBody = { title, messages: messages.map(toSavedMessage) }
  const response = await authFetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(await errorDetail(response, 'Could not save this chat.'))
  return (await response.json()) as SavedChat
}

function toSavedMessage(message: Message): SavedChatMessage {
  const analysis = message.analysis
  const papers = message.results ?? []
  const citations = (analysis?.citations ?? []).map((citation) => {
    const paper = papers.find((candidate) => candidate.paper_id === citation.paper_id)
    return {
      ...citation,
      paper_pmid: paper?.pmid ?? null,
      paper_title: paper?.title ?? null,
    }
  })
  return {
    id: message.id,
    role: message.role,
    content: analysis ? (analysis.answer ?? '') : message.text,
    status: message.status === 'error' ? 'error' : 'done',
    fallback_text: analysis ? message.text : null,
    response_kind: analysis ? 'paper_analysis' : papers.length > 0 ? 'paper_search' : null,
    result_papers: papers,
    papers_considered: message.papersConsidered ?? 0,
    analysis_entity_ids: analysis?.entity_ids ?? [],
    analysis_duplicates_rejected: analysis?.duplicates_rejected ?? 0,
    analysis_model: analysis?.model ?? null,
    analysis_error: analysis?.error ?? null,
    citations,
    entity_pills: message.answerEntities ?? [],
  }
}

function fromSavedMessage(message: SavedChatMessage): Message {
  const analysis = savedAnalysis(message)
  return {
    id: message.id,
    role: message.role,
    text: message.fallback_text ?? message.content,
    status: message.status,
    results: message.result_papers.length > 0 ? message.result_papers : undefined,
    analysis,
    answerPending: false,
    answerEntities: message.entity_pills
      .filter((entity): entity is AnswerEntity => entity.entity_id !== null),
    answerEntitiesPending: false,
    papersConsidered: message.papers_considered,
  }
}

function savedAnalysis(message: SavedChatMessage): PaperAnalysisResult | undefined {
  if (message.response_kind !== 'paper_analysis') return undefined
  return {
    answer: message.content || null,
    citations: message.citations,
    entity_ids: message.analysis_entity_ids,
    duplicates_rejected: message.analysis_duplicates_rejected,
    model: message.analysis_model,
    error: message.analysis_error,
  }
}

async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    // Keep the caller's stable fallback for a non-JSON response.
  }
  return fallback
}
