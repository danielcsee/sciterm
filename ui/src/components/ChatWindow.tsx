import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth'
import type { Citation } from '../api'
import RagResults from './RagResults'
import type { Message } from '../types'
import AnalysisMessage from './AnalysisMessage'
import EntityMatchResults from './EntityMatchResults'
import DebugDisclosure from './DebugDisclosure'
import IntentEntityList from './IntentEntityList'

const EXAMPLES = [
  'What is known about BRCA1 and DNA repair?',
  'Which findings about osteoporosis and quality of life conflict?',
  'Summarise the evidence linking calcium intake to fracture risk.',
]

/** Must match the .landing-exit transition in styles.css. */
const LANDING_EXIT_MS = 320

interface Props {
  messages: Message[]
  onSend: (text: string) => void
  onOpenPaper: (paperId: number, title: string | null) => void
  /** Open a cited paper at the paragraph, with `entityIds` highlighted. */
  onOpenCitation: (citation: Citation, entityIds: number[], title: string | null) => void
}

export default function ChatWindow({ messages, onSend, onOpenPaper, onOpenCitation }: Props) {
  // Asking a question runs retrieval on the server, so the composer is a
  // gate. Locked it stays readable and clickable — clicking is what opens the
  // modal, which a `disabled` control could never do: disabled elements fire
  // no click events at all.
  const { unlocked, requireAuth } = useAuth()
  const [draft, setDraft] = useState('')
  // The landing block outlives the first question: it has to animate away
  // before the answer appears, rather than vanishing the instant state changes.
  const [landingVisible, setLandingVisible] = useState(messages.length === 0)
  const [landingLeaving, setLandingLeaving] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  const asked = messages.length > 0
  // Scroll to the end for a new message or a finished search, but not for
  // each piece of a streaming answer: that would drag the reader along.
  const lastStatus = messages[messages.length - 1]?.status

  useEffect(() => {
    if (!asked || !landingVisible) return
    setLandingLeaving(true)
    const timer = window.setTimeout(() => {
      setLandingVisible(false)
      setLandingLeaving(false)
    }, LANDING_EXIT_MS)
    return () => window.clearTimeout(timer)
  }, [asked, landingVisible])

  useEffect(() => {
    if (landingVisible) return
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, lastStatus, landingVisible])

  function openCitation(message: Message, citation: Citation) {
    const paper = message.results?.find((result) => result.paper_id === citation.paper_id)
    onOpenCitation(citation, message.analysis?.entity_ids ?? [], paper?.title ?? null)
  }

  /** The work, past the gate. Must not call `submit` — see below. */
  function send(text: string) {
    onSend(text)
    setDraft('')
  }

  function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return
    // The gate runs `send`, never `submit`. Handing `submit` to requireAuth
    // would recurse without end: unlocked, requireAuth runs its action
    // immediately, and that action would gate itself again.
    requireAuth(() => send(trimmed))
  }

  return (
    <section className="chat" aria-label="Chat">
      <div className="chat-scroll">
        {landingVisible && (
          <div className={`landing${landingLeaving ? ' landing-exit' : ''}`}>
            <h1 className="landing-title">Ask the literature a question</h1>
            <p className="landing-sub">
              Answers are grounded in the papers you have imported, ranked by
              how strongly their passages match your question.
            </p>
            <ul className="examples">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button
                    className="example"
                    onClick={() => submit(example)}
                    disabled={landingLeaving}
                  >
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Held back until the landing block has finished leaving, so the two
            never occupy the same space. */}
        {!landingVisible && (
          <ol className="messages">
            {messages.map((message, index) => (
              <li key={message.id} className={`message message-${message.role}`}>
                <div className="message-role">
                  {message.role === 'user' ? 'You' : 'sciterm'}
                </div>
                <div className="message-body">
                  {message.status === 'pending' ? (
                    <span className="rag-pending" role="status">
                      <span className="spinner" aria-hidden="true" />
                      <span>{message.text}</span>
                    </span>
                  ) : (
                    <>
                      {message.analysis ? (
                        <AnalysisMessage
                          analysis={message.analysis}
                          papers={message.results ?? []}
                          pending={message.answerPending ?? false}
                          fallbackText={message.text}
                          isLatest={index === messages.length - 1}
                          onOpenPaper={onOpenPaper}
                          onOpenCitation={(citation) => openCitation(message, citation)}
                        />
                      ) : (
                        <>
                          {message.text && <p className="rag-text">{message.text}</p>}
                          {message.results && (
                            <RagResults
                              papers={message.results}
                              papersConsidered={message.papersConsidered ?? 0}
                              onOpenPaper={onOpenPaper}
                            />
                          )}
                        </>
                      )}
                      {message.entityMatches && (
                        <DebugDisclosure>
                          <DebugDisclosure label="Raw Candidates">
                            <EntityMatchResults groups={message.entityMatches} />
                          </DebugDisclosure>
                          <DebugDisclosure label="Filtered Candidates">
                            <EntityMatchResults groups={message.filteredEntityMatches ?? []} />
                          </DebugDisclosure>
                          {message.intentEntities && (
                            <DebugDisclosure label="OpenAI Entities">
                              <IntentEntityList entities={message.intentEntities} />
                            </DebugDisclosure>
                          )}
                        </DebugDisclosure>
                      )}
                    </>
                  )}
                </div>
              </li>
            ))}
            <div ref={endRef} />
          </ol>
        )}
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault()
          submit(draft)
        }}
      >
        <textarea
          className="composer-input"
          value={draft}
          readOnly={!unlocked}
          onMouseDown={(event) => {
            if (unlocked) return
            // Prevent the caret landing in a field that cannot be typed into.
            event.preventDefault()
            requireAuth()
          }}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit(draft)
            }
          }}
          rows={1}
          placeholder={
            unlocked
              ? 'Ask a question about your corpus…'
              : 'Enter an access code to ask a question…'
          }
          aria-label="Message"
        />
        <button
          className="composer-send"
          type="submit"
          // Enabled while locked so the click can open the modal; the empty
          // draft is not the reason it cannot be used yet.
          disabled={unlocked && !draft.trim()}
          onClick={(event) => {
            if (unlocked) return
            event.preventDefault()
            requireAuth()
          }}
        >
          Send
        </button>
      </form>
    </section>
  )
}
