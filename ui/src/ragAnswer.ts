import { ApiError, type RagSearchResponse, type RagStreamEvent } from './api'
import type { Message } from './types'

/** Shown when the connection closes before the answer says it is finished. */
const CUT_OFF = 'The answer stopped arriving before it was finished.'

/**
 * The message text: an analysis's failure when it has no answer to show, or
 * else the routed tool's name, or why there is none.
 */
export function intentText(response: RagSearchResponse): string {
  const analysis = response.analysis
  if (analysis?.error && !analysis.answer) return `Could not write an answer: ${analysis.error}`
  if (response.intent) return `Tool: ${response.intent.tool}`
  return `Tool: none (${response.intent_error ?? 'intent routing did not run'})`
}

/** Fold one line of the `rag_search` stream into the assistant's message. */
export function applyRagEvent(
  message: Message,
  event: RagStreamEvent,
  response: RagSearchResponse | null,
): Message {
  switch (event.type) {
    case 'result':
      return resultMessage(message, event.result)
    case 'answer_delta':
      if (!message.analysis) return message
      return {
        ...message,
        analysis: { ...message.analysis, answer: (message.analysis.answer ?? '') + event.text },
      }
    case 'answer_done':
      if (!message.analysis || !response) return message
      return finishAnswer(message, response, event.answer, event.model, event.error)
  }
}

/**
 * Close an answer the stream never finished, so no spinner outlives the
 * connection. A no-op once `answer_done` has arrived.
 */
export function endRagStream(message: Message, response: RagSearchResponse | null): Message {
  if (!message.answerPending || !message.analysis || !response) return message
  return finishAnswer(message, response, null, null, CUT_OFF)
}

/** The search itself failed: nothing arrived to show. */
export function searchFailed(message: Message, err: unknown): Message {
  return {
    ...message,
    status: 'error',
    text: err instanceof ApiError ? err.message : 'Could not reach the search service.',
    results: undefined,
    analysis: undefined,
    answerPending: undefined,
    entityMatches: undefined,
    filteredEntityMatches: undefined,
    intentEntities: undefined,
  }
}

function resultMessage(message: Message, response: RagSearchResponse): Message {
  const analysis = response.analysis ?? undefined
  return {
    ...message,
    status: 'done',
    text: intentText(response),
    // No search ran for `no_match`, so there is no result list to show.
    results: response.search_method ? response.papers : undefined,
    analysis,
    // The server already knows when no answer will be written.
    answerPending: analysis !== undefined && !analysis.error,
    papersConsidered: response.papers_considered,
    entityMatches: response.entity_matches,
    filteredEntityMatches: response.filtered_entity_matches,
    intentEntities: response.intent?.entities,
  }
}

function finishAnswer(
  message: Message,
  response: RagSearchResponse,
  answer: string | null,
  model: string | null,
  error: string | null,
): Message {
  const analysis = { ...message.analysis!, answer, model, error }
  return {
    ...message,
    analysis,
    answerPending: false,
    text: intentText({ ...response, analysis }),
  }
}
