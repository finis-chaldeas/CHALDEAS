import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sourcesApi } from '../../api/client'
import type { SourceDetail, SourcePerson, SourceMention } from '../../types'

type SourceTab = 'content' | 'persons' | 'mentions'

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
      <div className="source-skeleton-list">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="source-skeleton" style={{ height: '2rem' }} />
        ))}
      </div>
    )
  }

  if (!persons || persons.length === 0) {
    return <p className="source-mention-context">No persons mentioned in this source.</p>
  }

  const sorted = [...persons].sort((a, b) => b.mention_count - a.mention_count)
  const maxMentions = Math.max(...sorted.map((p) => p.mention_count), 1)

  return (
    <div>
      {sorted.map((p) => (
        <button
          key={p.id}
          onClick={() => onPersonClick(p.id)}
          className="source-person-item"
        >
          <div className="source-person-row">
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', minWidth: 0, flex: 1 }}>
              <span className="source-person-name">{p.name}</span>
              {p.role && <span className="source-person-role">({p.role})</span>}
            </div>
            <span className="source-person-count">{p.mention_count}x</span>
          </div>
          <div className="source-person-bar">
            <div
              className="source-person-bar-fill"
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
      <div className="source-skeleton-list">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="source-skeleton" style={{ height: '3rem' }} />
        ))}
      </div>
    )
  }

  if (!mentions || mentions.length === 0) {
    return <p className="source-mention-context">No mentions recorded for this source.</p>
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
        <span className="source-mention-highlight">{match}</span>
        {after}
      </>
    )
  }

  const nameClass: Record<string, string> = {
    person: 'source-mention-name--person',
    event: 'source-mention-name--event',
    location: 'source-mention-name--location',
  }

  return (
    <div>
      {mentions.map((m) => (
        <div key={m.id} className="source-mention-item">
          <div className="source-mention-header">
            <span className={`source-mention-name ${nameClass[m.entity_type] || ''}`}>
              {m.entity_name}
            </span>
            <span className="source-mention-type-tag">{m.entity_type}</span>
          </div>
          {m.context && (
            <p className="source-mention-context">
              "...{highlightEntity(m.context, m.entity_name)}..."
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Wiki Content Tab ──────────────────────────────────────

function SourceWikiContent({ sourceId }: { sourceId: number }) {
  const { data: wiki, isLoading } = useQuery({
    queryKey: ['source-wiki', sourceId],
    queryFn: () => sourcesApi.getWiki(sourceId),
    select: (res) => res.data as {
      source_id: number
      title: string
      content_html?: string | null
      content_text?: string | null
      word_count?: number
      external_url?: string
      status: string
    },
  })

  if (isLoading) {
    return (
      <div className="source-skeleton-detail">
        <div className="source-skeleton source-skeleton-body" />
      </div>
    )
  }

  if (!wiki) return null

  // If we have HTML content, render it
  if (wiki.status === 'ok' && wiki.content_html) {
    return (
      <div className="source-wiki-container">
        {wiki.word_count && (
          <div style={{ fontSize: '0.65rem', color: 'var(--chaldea-text)', marginBottom: '0.75rem' }}>
            {wiki.word_count.toLocaleString()} words
          </div>
        )}
        <div
          className="source-wiki-content"
          dangerouslySetInnerHTML={{ __html: wiki.content_html }}
        />
        {wiki.external_url && (
          <div className="source-detail-footer">
            <a
              href={wiki.external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-detail-external"
            >
              View on Wikipedia &rarr;
            </a>
          </div>
        )}
      </div>
    )
  }

  // Fallback: plain text
  if (wiki.status === 'ok' && wiki.content_text) {
    return (
      <div className="source-wiki-container">
        <div className="source-text">{wiki.content_text}</div>
        {wiki.external_url && (
          <div className="source-detail-footer">
            <a
              href={wiki.external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-detail-external"
            >
              View on Wikipedia &rarr;
            </a>
          </div>
        )}
      </div>
    )
  }

  // ZIM not found or other status — show external link
  if (wiki.external_url) {
    return (
      <div className="source-wiki-container">
        <div className="source-status">
          {wiki.status === 'zim_not_found'
            ? 'Local Wikipedia archive not available. View the article online.'
            : wiki.status === 'article_not_found'
              ? 'Article not found in local archive. View it online.'
              : 'Content unavailable locally.'}
        </div>
        <a
          href={wiki.external_url}
          target="_blank"
          rel="noopener noreferrer"
          className="source-detail-external"
        >
          Read on Wikipedia &rarr;
        </a>
      </div>
    )
  }

  return null
}

// ─── Source Detail Panel ────────────────────────────────────

interface SourceDetailPanelProps {
  sourceId: number
  onBack: () => void
  onPersonClick: (personId: number) => void
}

export function SourceDetailPanel({ sourceId, onBack, onPersonClick }: SourceDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<SourceTab>('content')

  const { data: source, isLoading, isError } = useQuery({
    queryKey: ['source', sourceId],
    queryFn: () => sourcesApi.get(sourceId),
    select: (res) => res.data as SourceDetail,
  })

  const typeClass: Record<string, string> = {
    book: 'source-type-tag--book',
    wikipedia: 'source-type-tag--wikipedia',
    wikidata: 'source-type-tag--wikidata',
    article: 'source-type-tag--article',
  }

  return (
    <div className="source-detail">
      {/* Back */}
      <div className="source-detail-header">
        <button onClick={onBack} className="source-detail-back" title="Back to source list">
          &larr;
        </button>
        <span className="source-detail-breadcrumb">Sources</span>
      </div>

      <div className="source-detail-body">
        {isLoading && (
          <div className="source-skeleton-detail">
            <div className="source-skeleton source-skeleton-title" />
            <div className="source-skeleton source-skeleton-author" />
            <div className="source-skeleton source-skeleton-body" />
          </div>
        )}

        {isError && (
          <div className="source-error">Failed to load source details.</div>
        )}

        {source && (
          <>
            {/* Header */}
            <div className="source-detail-title-row">
              <h2 className="source-detail-title">{source.title}</h2>
              <span className={`source-type-tag ${typeClass[source.type] || ''}`}>
                {source.type}
              </span>
            </div>
            {source.author && (
              <p className="source-detail-author">by {source.author}</p>
            )}

            {/* Stats */}
            <div className="source-detail-stats">
              {source.mention_count !== undefined && source.mention_count > 0 && (
                <div className="source-detail-stat">
                  <span className="source-detail-stat-dot source-detail-stat-dot--cyan" />
                  <span><span className="source-detail-stat-value">{source.mention_count}</span> mentions</span>
                </div>
              )}
              {source.person_count !== undefined && source.person_count > 0 && (
                <div className="source-detail-stat">
                  <span className="source-detail-stat-dot source-detail-stat-dot--gold" />
                  <span><span className="source-detail-stat-value">{source.person_count}</span> persons</span>
                </div>
              )}
              {source.event_count !== undefined && source.event_count > 0 && (
                <div className="source-detail-stat">
                  <span className="source-detail-stat-dot source-detail-stat-dot--orange" />
                  <span><span className="source-detail-stat-value">{source.event_count}</span> events</span>
                </div>
              )}
            </div>

            {/* Tab bar */}
            <div className="source-tab-bar">
              {([
                { key: 'content' as SourceTab, label: 'Article' },
                { key: 'persons' as SourceTab, label: 'Persons' },
                { key: 'mentions' as SourceTab, label: 'Mentions' },
              ]).map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`source-tab-btn ${activeTab === tab.key ? 'source-tab-btn--active' : ''}`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === 'content' && <SourceWikiContent sourceId={sourceId} />}
            {activeTab === 'persons' && <SourcePersonsTab sourceId={sourceId} onPersonClick={onPersonClick} />}
            {activeTab === 'mentions' && <SourceMentionsTab sourceId={sourceId} />}

            {/* External link (only if not showing in content tab) */}
            {activeTab !== 'content' && source.url && (
              <div className="source-detail-footer">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-detail-external"
                >
                  View Source &rarr;
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
