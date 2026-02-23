import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sourcesApi } from '../../api/client'
import type { SourceDetail, SourcePerson, SourceMention } from '../../types'

type SourceTab = 'persons' | 'mentions'

// ─── Source Persons Tab ─────────────────────────────────────

function SourcePersonsTab({
  sourceId,
  onPersonClick,
}: {
  sourceId: number
  onPersonClick: (personId: number) => void
}) {
  const { data: persons, isLoading } = useQuery({
    queryKey: ['source-persons', sourceId],
    queryFn: () => sourcesApi.getPersons(sourceId),
    select: (res) => (res.data.persons ?? res.data) as SourcePerson[],
  })

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-8 bg-chaldea-border rounded" />
        ))}
      </div>
    )
  }

  if (!persons || persons.length === 0) {
    return <p className="text-xs text-chaldea-text italic">No persons mentioned in this source.</p>
  }

  const sorted = [...persons].sort((a, b) => b.mention_count - a.mention_count)
  const maxMentions = Math.max(...sorted.map((p) => p.mention_count), 1)

  return (
    <div className="space-y-1">
      {sorted.map((p) => (
        <button
          key={p.id}
          onClick={() => onPersonClick(p.id)}
          className="w-full text-left px-3 py-2 rounded text-xs border border-chaldea-border
                     hover:bg-chaldea-cyan/10 transition-colors group"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-baseline gap-1.5 min-w-0 flex-1">
              <span className="text-chaldea-text-bright truncate group-hover:text-chaldea-cyan transition-colors">
                {p.name}
              </span>
              {p.role && (
                <span className="text-chaldea-text text-[10px] shrink-0">({p.role})</span>
              )}
            </div>
            <span className="text-chaldea-text text-[10px] shrink-0">
              {p.mention_count}x
            </span>
          </div>
          <div className="mt-1 h-[2px] bg-chaldea-border rounded-full overflow-hidden">
            <div
              className="h-full bg-chaldea-gold rounded-full transition-all"
              style={{ width: `${(p.mention_count / maxMentions) * 100}%` }}
            />
          </div>
        </button>
      ))}
    </div>
  )
}

// ─── Source Mentions Tab ────────────────────────────────────

function SourceMentionsTab({ sourceId }: { sourceId: number }) {
  const { data: mentions, isLoading } = useQuery({
    queryKey: ['source-mentions', sourceId],
    queryFn: () => sourcesApi.getMentions(sourceId, { limit: 20 }),
    select: (res) => (res.data.mentions ?? res.data) as SourceMention[],
  })

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-12 bg-chaldea-border rounded" />
        ))}
      </div>
    )
  }

  if (!mentions || mentions.length === 0) {
    return <p className="text-xs text-chaldea-text italic">No mentions recorded for this source.</p>
  }

  function highlightEntity(context: string, entityName: string): JSX.Element {
    const lowerContext = context.toLowerCase()
    const lowerName = entityName.toLowerCase()
    const idx = lowerContext.indexOf(lowerName)

    if (idx === -1) return <>{context}</>

    const before = context.slice(0, idx)
    const match = context.slice(idx, idx + entityName.length)
    const after = context.slice(idx + entityName.length)

    return (
      <>
        {before}
        <span className="text-chaldea-cyan font-medium">{match}</span>
        {after}
      </>
    )
  }

  const entityTypeBadge: Record<string, string> = {
    person: 'text-chaldea-cyan',
    event: 'text-chaldea-orange',
    location: 'text-chaldea-green',
  }

  return (
    <div className="space-y-2">
      {mentions.map((m) => (
        <div
          key={m.id}
          className="px-3 py-2 rounded border border-chaldea-border text-xs"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-medium ${entityTypeBadge[m.entity_type] || 'text-chaldea-text-bright'}`}>
              {m.entity_name}
            </span>
            <span className="text-[9px] text-chaldea-text uppercase px-1 py-0.5 rounded border border-chaldea-border">
              {m.entity_type}
            </span>
          </div>
          {m.context && (
            <p className="text-[11px] text-chaldea-text leading-relaxed italic">
              "...{highlightEntity(m.context, m.entity_name)}..."
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Source Detail Panel ────────────────────────────────────

interface SourceDetailPanelProps {
  sourceId: number
  onBack: () => void
  onPersonClick: (personId: number) => void
}

export function SourceDetailPanel({ sourceId, onBack, onPersonClick }: SourceDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<SourceTab>('persons')

  const { data: source, isLoading, isError } = useQuery({
    queryKey: ['source', sourceId],
    queryFn: () => sourcesApi.get(sourceId),
    select: (res) => res.data as SourceDetail,
  })

  const typeBadgeColor: Record<string, string> = {
    book: 'border-chaldea-gold text-chaldea-gold',
    wikipedia: 'border-chaldea-cyan text-chaldea-cyan',
    wikidata: 'border-chaldea-green text-chaldea-green',
    article: 'border-chaldea-magenta text-chaldea-magenta',
  }

  return (
    <div className="flex flex-col h-full">
      {/* Back */}
      <div className="flex items-center gap-2 p-3 border-b border-chaldea-border">
        <button
          onClick={onBack}
          className="w-7 h-7 flex items-center justify-center rounded border border-chaldea-border
                     text-chaldea-text hover:text-chaldea-cyan hover:border-chaldea-cyan transition-colors text-sm"
          title="Back to source list"
        >
          &larr;
        </button>
        <span className="text-xs text-chaldea-text">Sources</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="p-6">
            <div className="animate-pulse space-y-3">
              <div className="h-5 bg-chaldea-border rounded w-3/4" />
              <div className="h-3 bg-chaldea-border rounded w-1/2" />
              <div className="h-16 bg-chaldea-border rounded" />
            </div>
          </div>
        )}

        {isError && (
          <div className="p-6">
            <p className="text-sm text-chaldea-magenta">Failed to load source details.</p>
          </div>
        )}

        {source && (
          <div className="p-5 space-y-4">
            {/* Header */}
            <div>
              <div className="flex items-start gap-2">
                <h2 className="text-lg font-semibold text-chaldea-text-bright leading-tight flex-1">
                  {source.title}
                </h2>
                <span
                  className={`shrink-0 mt-1 px-1.5 py-0.5 rounded text-[10px] uppercase border ${
                    typeBadgeColor[source.type] || 'border-chaldea-border text-chaldea-text'
                  }`}
                >
                  {source.type}
                </span>
              </div>
              {source.author && (
                <p className="text-sm text-chaldea-text mt-1">by {source.author}</p>
              )}
            </div>

            {/* Stats */}
            <div className="flex items-center gap-4 text-xs">
              {source.mention_count !== undefined && source.mention_count > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-chaldea-cyan" />
                  <span className="text-chaldea-text">
                    <span className="text-chaldea-text-bright font-medium">{source.mention_count}</span> mentions
                  </span>
                </div>
              )}
              {source.person_count !== undefined && source.person_count > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-chaldea-gold" />
                  <span className="text-chaldea-text">
                    <span className="text-chaldea-text-bright font-medium">{source.person_count}</span> persons
                  </span>
                </div>
              )}
              {source.event_count !== undefined && source.event_count > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-chaldea-orange" />
                  <span className="text-chaldea-text">
                    <span className="text-chaldea-text-bright font-medium">{source.event_count}</span> events
                  </span>
                </div>
              )}
            </div>

            {/* Tab bar */}
            <div className="flex border-b border-chaldea-border">
              {([
                { key: 'persons' as SourceTab, label: 'Persons Mentioned' },
                { key: 'mentions' as SourceTab, label: 'Mentions' },
              ]).map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px ${
                    activeTab === tab.key
                      ? 'text-chaldea-cyan border-chaldea-cyan'
                      : 'text-chaldea-text border-transparent hover:text-chaldea-text-bright hover:border-chaldea-border'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div>
              {activeTab === 'persons' && <SourcePersonsTab sourceId={sourceId} onPersonClick={onPersonClick} />}
              {activeTab === 'mentions' && <SourceMentionsTab sourceId={sourceId} />}
            </div>

            {/* Read Full link */}
            {source.url && (
              <div className="border-t border-chaldea-border pt-3">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-chaldea-cyan hover:underline"
                >
                  Read Full Source
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
