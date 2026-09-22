import { authFetch } from '../auth/session'
import type { AnswerEntity, Citation, PaperAnalysisResult, SearchedPaper } from '../api'
import type { Message, MessageStatus, Role } from '../types'
import type { UserAnnotation } from '../define'

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
  status: MessageStatus
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

export interface SavedChat {
  chat_id: number
  title: string
  messages: SavedChatMessage[]
  annotations: UserAnnotation[]
  created_at: string
  updated_at: string
}

export interface ChatTurn {
  user_message_id: string
  assistant_message_id: string
  content: string
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

/** Permanently removes a chat, with its messages and annotations. */
export async function deleteSavedChat(chatId: number): Promise<void> {
  const response = await authFetch(`/chats/${chatId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(await errorDetail(response, 'Could not delete that chat.'))
}

export async function startChat(turn: ChatTurn): Promise<SavedChat> {
  return writeTurn('/chats', turn)
}

export async function appendChatTurn(
  chatId: number,
  turn: ChatTurn,
): Promise<SavedChat> {
  return writeTurn(`/chats/${chatId}/turns`, turn)
}

export function savedMessages(chat: SavedChat): Message[] {
  return chat.messages.map(fromSavedMessage)
}

export function suggestedChatTitle(messages: readonly Message[]): string {
  const query = messages.find((message) => message.role === 'user')?.text.trim()
  if (!query) return 'Saved conversation'
  return query.slice(0, 20)
}

async function writeTurn(
  url: string,
  turn: ChatTurn,
): Promise<SavedChat> {
  const response = await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(turn),
  })
  if (!response.ok) throw new Error(await errorDetail(response, 'Could not save this message.'))
  return (await response.json()) as SavedChat
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
