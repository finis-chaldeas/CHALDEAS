import { useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { portalApi, shiftsApi } from '../../api/client'
import { MarkdownText } from './MarkdownText'
import type { PortalItemDetail as PortalItemDetailType } from '../../types'

interface RelatedShift {
  id: number
  title: string
  title_ko?: string
  chain_type?: string
  page_count?: number
}

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  slug: string
  onFlyToLocation: (lat: number, lng: number) => void
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift?: (shiftId: number) => void
}

export function PortalItemDetail({ slug, onFlyToLocation: _onFlyToLocation, onGlobeView, onOpenShift }: Props) {
  const { t } = useTranslation()
  const close = usePortalStore((s) => s.close)
  const suspend = usePortalStore((s) => s.suspend)
  const pop = usePortalStore((s) => s.pop)
  const openPreview = usePortalStore((s) => s.openPreview)
  const { preferredLanguage } = useSettingsStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: item, isLoading } = useQuery<PortalItemDetailType>({
    queryKey: ['portal-item', slug],
    queryFn: async () => {
      const res = await portalApi.getItem(slug)
      return res.data
    },
  })

  // Fetch related shifts by year range (±200 years)
  const { data: relatedShifts } = useQuery<RelatedShift[]>({
    queryKey: ['portal-related-shifts', item?.year],
    queryFn: async () => {
      if (!item?.year) return []
      const res = await shiftsApi.list({
        year_start: item.year - 200,
        year_end: item.year + 200,
        limit: 3,
      })
      return res.data?.items || res.data || []
    },
    enabled: !!item?.year,
    staleTime: 5 * 60 * 1000,
  })

  const scrollToSection = useCallback((index: number) => {
    const el = document.getElementById(`portal-section-${index}`)
    if (el && scrollRef.current) {
      const containerTop = scrollRef.current.getBoundingClientRect().top
      const elTop = el.getBoundingClientRect().top
      scrollRef.current.scrollTop += elTop - containerTop - 16
    }
  }, [])

  if (isLoading) {
    return (
      <div className="portal-modal">
        <div className="portal-header">
          <div className="portal-header__left">
            <button className="portal-header__back" onClick={pop}>{'\u2190'}</button>
            <span className="portal-header__title">Loading...</span>
          </div>
          <button className="portal-header__close" onClick={close}>{'\u2715'}</button>
        </div>
        <div className="portal-scroll">
          <div className="portal-skeleton" style={{ height: 24, width: '50%', marginBottom: 12 }} />
          <div className="portal-skeleton" style={{ height: 16, width: '70%', marginBottom: 8 }} />
          <div className="portal-skeleton" style={{ height: 100, width: '100%', marginBottom: 16 }} />
        </div>
      </div>
    )
  }

  if (!item) return null

  const title = getLocalizedText(item, 'title', preferredLanguage)
  const subtitle = item.subtitle ? getLocalizedText(item, 'subtitle', preferredLanguage) : undefined
  const description = getLocalizedText(item, 'description', preferredLanguage)
  const historicalBasis = item.historical_basis
    ? getLocalizedText(item, 'historical_basis', preferredLanguage)
    : undefined

  const meta = [item.era, item.year ? formatYear(item.year) : null, item.location]
    .filter(Boolean)
    .join(' \u00B7 ')

  const hasSections = item.sections && item.sections.length > 0
  const hasRelatedShifts = relatedShifts && relatedShifts.length > 0
  const hasRelatedServants = item.related_servants && item.related_servants.length > 0
  const hasSources = item.sources && item.sources.length > 0

  return (
    <div className="portal-modal">
      <div className="portal-header">
        <div className="portal-header__left">
          <button className="portal-header__back" onClick={pop}>{'\u2190'}</button>
          <span className="portal-header__title" style={{ fontSize: 12 }}>{title}</span>
        </div>
        <button className="portal-header__close" onClick={close}>{'\u2715'}</button>
      </div>

      <div className="portal-scroll" ref={scrollRef}>
        <div className="portal-article">
          {/* Badge */}
          <span className={`portal-detail__badge portal-hero-badge--${item.item_type}`}>
            {t(`trismegistos.types.${item.item_type}`, item.item_type.replace('_', ' '))}
          </span>

          {/* Title */}
          <h1 className="portal-article__title">{title}</h1>
          {subtitle && <div className="portal-article__subtitle">{subtitle}</div>}
          {meta && <div className="portal-article__meta">{meta}</div>}

          {/* Description */}
          <MarkdownText text={description} className="portal-article__description" />

          {/* Table of Contents */}
          {hasSections && (
            <nav className="portal-toc">
              <div className="portal-toc__title">{t('trismegistos.contents')}</div>
              {item.sections.map((section, i) => {
                const secTitle = getLocalizedText(section, 'title', preferredLanguage)
                return (
                  <button
                    key={i}
                    className="portal-toc__item"
                    onClick={() => scrollToSection(i)}
                  >
                    {i + 1}. {secTitle}
                  </button>
                )
              })}
            </nav>
          )}

          {/* Historical Basis */}
          {historicalBasis && (
            <MarkdownText text={historicalBasis} className="portal-article__historical" />
          )}

          {/* Full Sections — no accordion, continuous scroll */}
          {hasSections && item.sections.map((section, i) => {
            const secTitle = getLocalizedText(section, 'title', preferredLanguage)
            const secContent = getLocalizedText(section, 'content', preferredLanguage)
            return (
              <div key={i} id={`portal-section-${i}`} className="portal-article__section">
                <h2 className="portal-article__section-title">
                  {i + 1}. {secTitle}
                </h2>
                <MarkdownText text={secContent} className="portal-article__section-content" />
              </div>
            )
          })}

          {/* Related Shifts */}
          {hasRelatedShifts && (
            <div className="portal-article__related">
              <h3 className="portal-article__related-title">{t('trismegistos.relatedShifts')}</h3>
              {relatedShifts!.map((shift) => (
                <button
                  key={shift.id}
                  className="portal-article__shift-card"
                  onClick={() => { close(); onOpenShift?.(shift.id) }}
                >
                  <span className="portal-article__shift-icon">{'\u25B6'}</span>
                  <span className="portal-article__shift-body">
                    <span className="portal-article__shift-name">
                      {preferredLanguage === 'ko' && shift.title_ko ? shift.title_ko : shift.title}
                    </span>
                    <span className="portal-article__shift-meta">
                      {shift.page_count ? `${shift.page_count} ${t('trismegistos.pages')}` : ''}
                      {shift.chain_type ? ` \u00B7 ${shift.chain_type.replace('_', ' ')}` : ''}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Related Servants */}
          {hasRelatedServants && (
            <div className="portal-article__related">
              <h3 className="portal-article__related-title">{t('trismegistos.relatedServants')}</h3>
              <div className="portal-servants-grid">
                {item.related_servants.map((servant, i) => (
                  <button
                    key={i}
                    className={`portal-servant-card ${servant.slug ? 'portal-servant-card--linked' : ''}`}
                    onClick={() => servant.slug && openPreview(servant.slug)}
                    disabled={!servant.slug}
                  >
                    <div className="portal-servant-card__name">{servant.name}</div>
                    {servant.class && (
                      <div className="portal-servant-card__class">
                        {servant.class}{servant.rarity ? ` \u2605${servant.rarity}` : ''}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {hasSources && (
            <div className="portal-article__related">
              <h3 className="portal-article__related-title">{t('trismegistos.sources')}</h3>
              <ul className="portal-sources-list">
                {item.sources.map((source, i) => (
                  <li key={i}>{source}</li>
                ))}
              </ul>
            </div>
          )}

          {/* CTA Buttons */}
          <div className="portal-article__cta">
            {item.year && (
              <button
                className="portal-btn portal-btn--secondary"
                onClick={() => {
                  suspend()
                  if (item.year) onGlobeView({
                    year: item.year,
                    eventId: item.related_event_ids?.[0],
                  })
                }}
              >
                {t('trismegistos.globeView')} ({formatYear(item.year)})
              </button>
            )}
            {hasRelatedShifts && (
              <button
                className="portal-btn portal-btn--primary"
                onClick={() => { close(); onOpenShift?.(relatedShifts![0].id) }}
              >
                {t('trismegistos.startShift')} ({relatedShifts![0].page_count || '?'} {t('trismegistos.pages')})
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
