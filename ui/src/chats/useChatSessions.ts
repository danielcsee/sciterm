import { useCallback, useMemo, useRef, useState } from 'react'
import type { Message } from '../types'
import { loadSavedChat, savedMessages, type SavedChat } from './api'

/**
 * Where a conversation's messages live: its chat id once the server has one,
 * or `draft` for the homepage's first question while that chat is created.
 */
export type SessionKey = number | 'draft'

export interface ChatSessions {
  /** The messages under `key`, or undefined if that chat is not loaded. */
  messagesFor: (key: SessionKey) => Message[] | undefined
  /** Why the last load of `chatId` failed, if it did. */
  errorFor: (chatId: number) => string | undefined
  append: (key: SessionKey, messages: Message[]) => void
  update: (key: SessionKey, messageId: string, change: (message: Message) => Message) => void
  /** Move the draft under the id the server just gave it. */
  adoptDraft: (chatId: number) => void
  /** Fetch a saved chat and store its messages. Throws on failure. */
  load: (chatId: number) => Promise<SavedChat>
  forget: (key: SessionKey) => void
}

/**
 * Every open conversation's messages, keyed by chat.
 *
 * The homepage and each chat tab read from here rather than sharing one list,
 * so an answer streaming into one conversation cannot land in another the
 * reader has switched to. The homepage's chat and a tab of the same chat
 * share one entry, so they never diverge.
 */
export function useChatSessions(): ChatSessions {
  const [sessions, setSessions] = useState<ReadonlyMap<SessionKey, Message[]>>(new Map())
  const [errors, setErrors] = useState<ReadonlyMap<number, string>>(new Map())
  // Loads already on the wire, so a re-render cannot fetch the same chat twice.
  const inflight = useRef<Map<number, Promise<SavedChat>>>(new Map())

  const write = useCallback(
    (key: SessionKey, change: (messages: Message[] | undefined) => Message[] | undefined) =>
      setSessions((prev) => withEntry(prev, key, change(prev.get(key)))),
    [],
  )

  const append = useCallback(
    (key: SessionKey, messages: Message[]) =>
      write(key, (current) => [...(current ?? []), ...messages]),
    [write],
  )

  const update = useCallback(
    (key: SessionKey, messageId: string, change: (message: Message) => Message) =>
      write(key, (current) =>
        current?.map((message) => (message.id === messageId ? change(message) : message)),
      ),
    [write],
  )

  const adoptDraft = useCallback(
    (chatId: number) =>
      setSessions((prev) => withEntry(withEntry(prev, chatId, prev.get('draft')), 'draft', undefined)),
    [],
  )

  const forget = useCallback((key: SessionKey) => write(key, () => undefined), [write])

  const load = useCallback(
    (chatId: number) => {
      const running = inflight.current.get(chatId)
      if (running) return running
      const request = fetchSession(chatId, write, setErrors).finally(() =>
        inflight.current.delete(chatId),
      )
      inflight.current.set(chatId, request)
      return request
    },
    [write],
  )

  const messagesFor = useCallback((key: SessionKey) => sessions.get(key), [sessions])
  const errorFor = useCallback((chatId: number) => errors.get(chatId), [errors])

  return useMemo(
    () => ({ messagesFor, errorFor, append, update, adoptDraft, load, forget }),
    [messagesFor, errorFor, append, update, adoptDraft, load, forget],
  )
}

function withEntry<K, V>(map: ReadonlyMap<K, V>, key: K, value: V | undefined): ReadonlyMap<K, V> {
  if (map.get(key) === value) return map
  const next = new Map(map)
  if (value === undefined) next.delete(key)
  else next.set(key, value)
  return next
}

async function fetchSession(
  chatId: number,
  write: (key: SessionKey, change: () => Message[]) => void,
  setErrors: (change: (prev: ReadonlyMap<number, string>) => ReadonlyMap<number, string>) => void,
): Promise<SavedChat> {
  try {
    const chat = await loadSavedChat(chatId)
    write(chatId, () => savedMessages(chat))
    setErrors((prev) => withEntry(prev, chatId, undefined))
    return chat
  } catch (error) {
    const reason = error instanceof Error ? error.message : 'Could not load that conversation.'
    setErrors((prev) => withEntry(prev, chatId, reason))
    throw error
  }
}
