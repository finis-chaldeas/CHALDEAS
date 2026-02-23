import { useState } from 'react'
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
      <div className="p-5">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-20 bg-chaldea-border rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (!sources || sources.length === 0) {
    return (
      <div className="p-5">
        <p className="text-sm text-chaldea-text">No sources available.</p>
      </div>
    )
  }

  const typeBadgeColor: Record<string, string> = {
    book: 'border-chaldea-gold text-chaldea-gold bg-chaldea-gold/5',
    wikipedia: 'border-chaldea-cyan text-chaldea-cyan bg-chaldea-cyan/5',
    wikidata: 'border-chaldea-green text-chaldea-green bg-chaldea-green/5',
    article: 'border-chaldea-magenta text-chaldea-magenta bg-chaldea-magenta/5',
  }

  return (
    <div className="p-5 space-y-4">
      <h2 className="text-lg font-semibold text-chaldea-text-bright">Sources</h2>
      <p className="text-xs text-chaldea-text">Browse reference materials and their mentions.</p>

      <div className="grid grid-cols-1 gap-2">
        {sources.map((src) => (
          <button
            key={src.id}
            onClick={() => onSelectSource(src.id)}
            className="text-left p-3 rounded border border-chaldea-border
                       hover:bg-chaldea-cyan/5 hover:border-chaldea-cyan/30 transition-colors group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm text-chaldea-text-bright truncate group-hover:text-chaldea-cyan transition-colors">
                  {src.title}
                </p>
                {src.author && (
                  <p className="text-[10px] text-chaldea-text mt-0.5 truncate">
                    by {src.author}
                  </p>
                )}
              </div>
              <span
                className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] uppercase border ${
                  typeBadgeColor[src.type] || 'border-chaldea-border text-chaldea-text'
                }`}
              >
                {src.type}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-2 text-[10px] text-chaldea-text">
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

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center"
      style={{ background: 'rgba(5, 8, 16, 0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
    >
      <div
        className="relative w-full max-w-lg max-h-[80vh] mx-4 rounded-lg border border-chaldea-border
                    flex flex-col overflow-hidden narrative-enter"
        style={{ background: '#0a1018f5', backdropFilter: 'blur(12px)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 w-7 h-7 flex items-center justify-center
                     rounded border border-chaldea-border text-chaldea-text
                     hover:text-chaldea-cyan hover:border-chaldea-cyan transition-colors text-sm"
        >
          x
        </button>

        {selectedSourceId ? (
          <SourceDetailPanel
            sourceId={selectedSourceId}
            onBack={() => setSelectedSourceId(null)}
            onPersonClick={onPersonClick}
          />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <SourceList onSelectSource={setSelectedSourceId} />
          </div>
        )}
      </div>
    </div>
  )
}
