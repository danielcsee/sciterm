import { useEffect, useState } from 'react'
import {
  ApiError,
  fetchImportedReferences,
  type ImportedReferenceList,
} from '../api'
import PaperCard from './PaperCard'

interface Props {
  paperId: number
  paperTitle: string
  onOpenPaper: (paperId: number, title: string | null) => void
  onClose: () => void
}

/** Imported papers whose bibliographies cite the selected paper. */
export default function ImportedReferences({
  paperId,
  paperTitle,
  onOpenPaper,
  onClose,
}: Props) {
  const [data, setData] = useState<ImportedReferenceList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchImportedReferences(paperId, controller.signal)
      .then(setData)
      .catch((err: unknown) => {
        if ((err as Error)?.name === 'AbortError') return
        setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [paperId])

  return (
    <>
      <div className="refs-head">
        <h2 className="imported-refs-title">Imported References</h2>
        <button className="refs-close" type="button" onClick={onClose} aria-label="Back to search">
          ✕
        </button>
      </div>

      <p className="refs-context" title={paperTitle}>
        Papers in your corpus that reference{' '}
        <span className="refs-context-title">{paperTitle}</span>
      </p>

      <div className="results">
        {loading && (
          <div className="results-loading" role="status" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <span>Loading imported references…</span>
          </div>
        )}
        {error && <p className="results-message results-error">{error}</p>}
        {!loading && !error && data && (
          <p className="search-count">
            {data.total} imported paper{data.total === 1 ? '' : 's'}
          </p>
        )}
        {!loading && !error && data?.papers.length === 0 && (
          <p className="results-message">
            No imported papers reference this paper yet.
          </p>
        )}

        <ul className="chips">
          {data?.papers.map((paper) => (
            <li key={paper.paper_id}>
              <button
                type="button"
                className="chip chip-openable"
                onClick={() => onOpenPaper(paper.paper_id, paper.title)}
                title="Open paper"
              >
                <PaperCard
                  title={paper.title}
                  journal={paper.journal}
                  year={paper.pub_year}
                  snippet={paper.snippet}
                  pmid={paper.pmid}
                  pmcid={paper.pmcid}
                />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}
