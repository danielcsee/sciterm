export interface AnnotationSource {
  chat_id: number | null
  chat_message_id: string | null
  paper_id: number | null
  paper_chunk_ordinal: number | null
  source_key: string
  quote_exact: string
  quote_prefix: string | null
  quote_suffix: string | null
  start_offset: number | null
  end_offset: number | null
}

export interface AnnotationDraft {
  id: string
  phrase: string
  surrounding_context: string | null
  source: AnnotationSource
}

export interface UserAnnotation extends AnnotationDraft {
  definition: string
  position: number
  created_at: string
  updated_at: string
}
