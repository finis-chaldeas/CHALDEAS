import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sourcesApi } from '../../api/client'
import type { SourceDetail } from '../../types'
import { SourceDetailPanel } from './SourceDetailPanel'

// ─── Source List ─────────────────────────────────────────────

function SourceList({ onSelectSource }: { onSelectSource: (id: number) => void }) {
  const { data: sources, isLoading } = useQuery({
    queryKey: ['sources-list'],
    queryFn: () => sourcesApi.list({ type: 'book', limit: 20 }),
    select: (res) => (res.data?.items ?? res.data?.sources ?? []) as SourceDetail[],
  })

  if (isLoading) {
    return (
      <div className="source-skeleton-list">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="source-skeleton source-skeleton-item" />
        ))}
      </div>
    )
  }

  if (!sources || sources.length === 0) {
    return (
      <div className="source-list-container">
        <p className="source-mention-context">No sources available.</p>
      </div>
    )
  }

  const typeClass: Record<string, string> = {
    book: 'source-type-tag--book',
    wikipedia: 'source-type-tag--wikipedia',
    wikidata: 'source-type-tag--wikidata',
    article: 'source-type-tag--article',
  }

  return (
    <div className="source-list-container">
      <h2 className="source-list-title">Sources</h2>
      <p className="source-list-subtitle">Browse reference materials and their mentions.</p>

      <div className="source-list-grid">
        {sources.map((src) => (
          <button
            key={src.id}
            onClick={() => onSelectSource(src.id)}
            className="source-list-item"
          >
            <div className="source-list-item-header">
              <div style={{ minWidth: 0, flex: 1 }}>
                <p className="source-list-item-title">{src.title}</p>
                {src.author && (
                  <p className="source-list-item-author">by {src.author}</p>
                )}
              </div>
              <span className={`source-type-tag ${typeClass[src.type] || ''}`}>
                {src.type}
              </span>
            </div>
            <div className="source-list-item-stats">
              {src.mention_count !== undefined && src.mention_count > 0 && (
                <span>{src.mention_count} mentions</span>
              )}
              {src.person_count !== undefined && src.person_count > 0 && (
                <span>{src.person_count} persons</span>
              )}
              {src.event_count !== undefined && src.event_count > 0 && (
                <span>{src.event_count} events</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Main SourceBrowser Component ───────────────────────────

interface SourceBrowserProps {
  isOpen: boolean
  onClose: () => void
  onPersonClick: (personId: number) => void
  initialSourceId?: number | null
}

export function SourceBrowser({ isOpen, onClose, onPersonClick, initialSourceId }: SourceBrowserProps) {
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(initialSourceId ?? null)

  // Sync when initialSourceId changes (e.g. clicking different source in narrative card)
  useEffect(() => {
    if (initialSourceId != null) {
      setSelectedSourceId(initialSourceId)
    }
  }, [initialSourceId])

  if (!isOpen) return null

  return (
    <div
      className="source-modal-backdrop"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
    >
      <div
        className="source-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button onClick={onClose} className="source-modal-close">
          {'\u2715'}
        </button>

        {selectedSourceId ? (
          <SourceDetailPanel
            sourceId={selectedSourceId}
            onBack={() => setSelectedSourceId(null)}
            onPersonClick={onPersonClick}
          />
        ) : (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <SourceList onSelectSource={setSelectedSourceId} />
          </div>
        )}
      </div>
    </div>
  )
}
