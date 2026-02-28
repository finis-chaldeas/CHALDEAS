import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { portalApi } from '../../api/client'
import type { PortalItemDetail as PortalItemDetailType } from '../../types'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  slug: string
  onFlyToLocation: (lat: number, lng: number) => void
  onGlobeView: (opts: GlobeViewOptions) => void
}

export function PortalItemDetail({ slug, onFlyToLocation: _onFlyToLocation, onGlobeView }: Props) {
  const close = usePortalStore((s) => s.close)
  const suspend = usePortalStore((s) => s.suspend)
  const pop = usePortalStore((s) => s.pop)
  const { preferredLanguage } = useSettingsStore()
  const [openSections, setOpenSections] = useState<Set<number>>(new Set([0]))

  const { data: item, isLoading } = useQuery<PortalItemDetailType>({
    queryKey: ['portal-item', slug],
    queryFn: async () => {
      const res = await portalApi.getItem(slug)
      return res.data
    },
  })

  const toggleSection = (index: number) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

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

  return (
    <div className="portal-modal">
      <div className="portal-header">
        <div className="portal-header__left">
          <button className="portal-header__back" onClick={pop}>{'\u2190'}</button>
          <span className="portal-header__title" style={{ fontSize: 12 }}>{title}</span>
        </div>
        <button className="portal-header__close" onClick={close}>{'\u2715'}</button>
      </div>

      <div className="portal-scroll">
        <div className="portal-detail">
          {/* Badge */}
          <span className={`portal-detail__badge portal-hero-badge--${item.item_type}`}>
            {item.item_type.replace('_', ' ')}
          </span>

          {/* Title */}
          <div className="portal-detail__title">{title}</div>
          {subtitle && <div className="portal-detail__subtitle">{subtitle}</div>}
          {meta && <div className="portal-detail__meta">{meta}</div>}

          {/* Description */}
          <div className="portal-detail__description">{description}</div>

          {/* Historical Basis */}
          {historicalBasis && (
            <div className="portal-section">
              <div className="portal-section__title">Historical Basis</div>
              <div className="portal-detail__historical">{historicalBasis}</div>
            </div>
          )}

          {/* Sections (accordion) */}
          {item.sections && item.sections.length > 0 && (
            <div className="portal-section">
              <div className="portal-section__title">Sections</div>
              {item.sections.map((section, i) => {
                const secTitle = getLocalizedText(section, 'title', preferredLanguage)
                const secContent = getLocalizedText(section, 'content', preferredLanguage)
                const isOpen = openSections.has(i)

                return (
                  <div key={i} className="portal-section-item">
                    <div
                      className="portal-section-item__header"
                      onClick={() => toggleSection(i)}
                    >
                      <span className="portal-section-item__header-title">{secTitle}</span>
                      <span className={`portal-section-item__toggle ${isOpen ? 'portal-section-item__toggle--open' : ''}`}>
                        {'\u25BC'}
                      </span>
                    </div>
                    {isOpen && (
                      <div className="portal-section-item__content">{secContent}</div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Related Servants */}
          {item.related_servants && item.related_servants.length > 0 && (
            <div className="portal-section">
              <div className="portal-section__title">Related Servants</div>
              <div className="portal-servants-grid">
                {item.related_servants.map((servant, i) => (
                  <div key={i} className="portal-servant-card">
                    <div className="portal-servant-card__name">{servant.name}</div>
                    {servant.class && (
                      <div className="portal-servant-card__class">
                        {servant.class}{servant.rarity ? ` \u2605${servant.rarity}` : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {item.sources && item.sources.length > 0 && (
            <div className="portal-section">
              <div className="portal-section__title">Sources</div>
              <ul className="portal-sources-list">
                {item.sources.map((source, i) => (
                  <li key={i}>{source}</li>
                ))}
              </ul>
            </div>
          )}

          {/* CTA */}
          {item.year && (
            <div style={{ marginTop: 24 }}>
              <button
                className="portal-btn portal-btn--primary"
                onClick={() => {
                  suspend()
                  if (item.year) onGlobeView({
                    year: item.year,
                    eventId: item.related_event_ids?.[0],
                  })
                }}
              >
                Globe View ({formatYear(item.year)})
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}
