import type {
  EntityMatchGroup,
  EntityStrategyGroup,
  IntentEntity,
  PaperAnalysisResult,
  SearchedPaper,
} from './api'

export type Role = 'user' | 'assistant'

export type MessageStatus = 'pending' | 'done' | 'error'

export interface Message {
  id: string
  role: Role
  text: string
  /** Assistant messages only: 'pending' while the search is in flight. */
  status?: MessageStatus
  /** Ranked papers backing an assistant answer. */
  results?: SearchedPaper[]
  /** A `paper_analysis` answer; its citations then replace the result list. */
  analysis?: PaperAnalysisResult
  /** How many papers matched any query term, before the top few were kept. */
  papersConsidered?: number
  /** Experimental entity candidates, kept grouped by discovery path. */
  entityMatches?: EntityMatchGroup[]
  /** The same candidates after dedupe, per-strategy top-n and score cutoff. */
  filteredEntityMatches?: EntityStrategyGroup[]
  /** Candidates OpenAI confirmed; undefined when intent routing did not run. */
  intentEntities?: IntentEntity[]
}

/** Open a paper at one cited paragraph, with the query's entities marked. */
export interface PaperFocus {
  paperId: number
  ordinal: number
  entityIds: number[]
  /** Distinguishes a second click on the same citation, so it re-scrolls. */
  nonce: number
}
