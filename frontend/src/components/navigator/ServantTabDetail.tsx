/**
 * ServantTabDetail - Inline servant detail view within the navigator
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { servantsApi } from '../../api/client'

interface BookMention {
  source_id: number
  source_title: string
  source_author?: string
  mention_count: number
  sample_contexts: string[]
}

interface ServantDetail {
  fgo_name: string
  fgo_class?: string
  rarity?: number
  origin?: string
  person_id?: number
  person_name?: string
  person_name_ko?: string
  wikidata_id?: string
  biography?: string
  birth_year?: number
  death_year?: number
  is_fgo_original: boolean
  mention_count: number
  book_mentions: BookMention[]
}

interface ServantTabDetailProps {
  fgoName: string
  onBack: () => void
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
}

function formatYear(year?: number) {
  if (!year) return null
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function rarityStars(rarity?: number): string {
  if (!rarity) return ''
  return '\u2605'.repeat(rarity)
}

export function ServantTabDetail({
  fgoName,
  onBack,
  onPersonClick,
  onSetCurrentYear,
}: ServantTabDetailProps) {
  const [expandedBook, setExpandedBook] = useState<number | null>(null)

  const { data: servant, isLoading } = useQuery<ServantDetail>({
    queryKey: ['servant-detail', fgoName],
    queryFn: async () => {
      const res = await servantsApi.get(fgoName)
      return res.data
    },
  })

  if (isLoading) {
    return <div className="navigator-loading">Loading servant detail...</div>
  }

  if (!servant) {
    return (
      <div className="servant-detail-inline">
        <button className="servant-detail-back" onClick={onBack}>
          {'\u2190'} Back to List
        </button>
        <div className="navigator-empty">Servant not found</div>
      </div>
    )
  }

  const handleExploreEra = () => {
    if (servant.birth_year && onSetCurrentYear) {
      const activeYear = servant.death_year
        ? Math.round((servant.birth_year + servant.death_year) / 2)
        : servant.birth_year
      onSetCurrentYear(activeYear)
    }
  }

  return (
    <div className="servant-detail-inline">
      <button className="servant-detail-back" onClick={onBack}>
        {'\u2190'} Back to List
      </button>

      {/* Name + rarity */}
      <div className="servant-detail-name">
        {servant.fgo_name}
        {servant.rarity && (
          <span style={{ color: '#fbbf24', fontSize: '0.8em', marginLeft: '0.5rem' }}>
            {rarityStars(servant.rarity)}
          </span>
        )}
        {servant.is_fgo_original && (
          <span className="servant-fgo-badge" style={{ marginLeft: '0.5rem' }}>FGO Original</span>
        )}
      </div>

      {/* Class + Origin */}
      {(servant.fgo_class || servant.origin) && (
        <div className="servant-detail-meta">
          {servant.fgo_class}{servant.origin && ` \u00B7 ${servant.origin}`}
        </div>
      )}

      {/* Historical connection */}
      {servant.person_name && (
        <>
          <div className="servant-detail-name" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            {servant.person_name}
            {servant.person_name_ko && (
              <span style={{ color: 'var(--chaldea-text)', opacity: 0.6, fontSize: '0.8em', marginLeft: '0.375rem' }}>
                ({servant.person_name_ko})
              </span>
            )}
          </div>

          {(servant.birth_year || servant.death_year) && (
            <div className="servant-detail-lifespan">
              {formatYear(servant.birth_year)} {'\u2013'} {formatYear(servant.death_year)}
            </div>
          )}

          {servant.biography && (
            <div className="servant-detail-bio">{servant.biography}</div>
          )}
        </>
      )}

      {/* Actions */}
      <div className="servant-detail-actions">
        {servant.person_id && onPersonClick && (
          <button
            className="servant-detail-action-btn primary"
            onClick={() => onPersonClick(servant.person_id!)}
          >
            View in CHALDEAS
          </button>
        )}
        {servant.birth_year && onSetCurrentYear && (
          <button
            className="servant-detail-action-btn"
            onClick={handleExploreEra}
          >
            Explore Era ({formatYear(servant.birth_year)})
          </button>
        )}
        {servant.wikidata_id && (
          <a
            href={`https://www.wikidata.org/wiki/${servant.wikidata_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="servant-detail-action-btn"
            style={{ textDecoration: 'none' }}
          >
            Wikidata {'\u2192'}
          </a>
        )}
      </div>

      {/* Book mentions */}
      {servant.book_mentions && servant.book_mentions.length > 0 && (
        <div className="servant-detail-books">
          <div className="servant-detail-books-title">
            Book Mentions ({servant.mention_count.toLocaleString()})
          </div>
          {servant.book_mentions.map(book => (
            <div key={book.source_id}>
              <button
                className="servant-detail-book"
                onClick={() => setExpandedBook(expandedBook === book.source_id ? null : book.source_id)}
                style={{ width: '100%', cursor: 'pointer', background: 'transparent', border: 'none', color: 'inherit' }}
              >
                <span style={{ flex: 1, textAlign: 'left' }}>
                  {book.source_title}
                  {book.source_author && <span style={{ opacity: 0.5 }}> by {book.source_author}</span>}
                </span>
                <span className="servant-detail-book-count">{book.mention_count}</span>
              </button>
              {expandedBook === book.source_id && book.sample_contexts.length > 0 && (
                <div style={{ paddingLeft: '0.75rem', marginBottom: '0.375rem' }}>
                  {book.sample_contexts.map((ctx, i) => (
                    <div key={i} style={{
                      fontSize: '0.58rem',
                      color: 'var(--chaldea-text)',
                      opacity: 0.6,
                      fontStyle: 'italic',
                      lineHeight: 1.4,
                      padding: '0.25rem 0',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                    }}>
                      &ldquo;...{ctx}...&rdquo;
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
