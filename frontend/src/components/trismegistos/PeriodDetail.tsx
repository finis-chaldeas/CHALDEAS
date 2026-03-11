import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { timelineApi, shiftsApi } from '../../api/client'
import { MarkdownText } from './MarkdownText'
import type { PeriodDetail as PeriodDetailType, HistoryShift } from '../../types'

interface Props {
  periodStart: number
  periodEnd: number
  onGlobeView: (year: number) => void
  onShiftClick: (shiftId: number) => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function PeriodDetail({
  periodStart,
  periodEnd,
  onGlobeView,
  onShiftClick,
  onEventClick,
  onPersonClick,
}: Props) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()
  const [expandedRegion, setExpandedRegion] = useState<string | null>(null)

  // Fetch period detail (on-demand)
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['period-detail', periodStart],
    queryFn: async () => {
      const res = await timelineApi.getPeriodDetail(periodStart, { event_limit: 10, person_limit: 10 })
      return res.data as PeriodDetailType
    },
  })

  // Fetch related shifts (on-demand)
  const { data: relatedShifts } = useQuery({
    queryKey: ['period-shifts', periodStart],
    queryFn: async () => {
      const res = await shiftsApi.list({
        year_start: periodStart,
        year_end: periodEnd,
        limit: 5,
      })
      // API may return { items: [...] } or just [...]
      const data = res.data
      return (data?.items ?? data) as HistoryShift[]
    },
  })

  if (detailLoading) {
    return (
      <div className="era-detail">
        <div className="portal-skeleton" style={{ height: 60, marginBottom: 12 }} />
        <div className="portal-skeleton" style={{ height: 40 }} />
      </div>
    )
  }

  if (!detail) return null

  const narrative = getLocalizedText(detail, 'narrative', preferredLanguage)

  return (
    <div className="era-detail">
      {/* Narrative */}
      {narrative && (
        <MarkdownText text={narrative} className="era-detail__narrative" />
      )}

      {/* Regions */}
      {detail.regions && detail.regions.length > 0 && (
        <div className="era-detail__section">
          <div className="era-detail__section-title">{t('trismegistos.era.regions')}</div>
          <div className="era-detail__regions">
            {detail.regions.map((region) => (
              <div key={region.region} className="era-region">
                <button
                  className="era-region__header"
                  onClick={() =>
                    setExpandedRegion(
                      expandedRegion === region.region ? null : region.region
                    )
                  }
                >
                  <span className="era-region__name">
                    {region.region_name}
                  </span>
                  <span className="era-region__stats">
                    ({region.event_count} {t('trismegistos.era.events')})
                  </span>
                  <span className={`era-region__toggle ${expandedRegion === region.region ? 'era-region__toggle--open' : ''}`}>
                    {'\u25B8'}
                  </span>
                </button>
                {expandedRegion === region.region && (
                  <div className="era-region__body">
                    {region.headline && (
                      <div className="era-region__headline">{region.headline}</div>
                    )}
                    {region.narrative && (
                      <MarkdownText text={region.narrative} className="era-region__narrative" />
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Events */}
      {detail.events && detail.events.length > 0 && (
        <div className="era-detail__section">
          <div className="era-detail__section-title">{t('trismegistos.era.keyEvents')}</div>
          <div className="era-detail__items">
            {detail.events.slice(0, 5).map((event) => {
              const title = getLocalizedText(event, 'title', preferredLanguage)
              return (
                <button
                  key={event.id}
                  className="era-item"
                  onClick={() => onEventClick(event.id)}
                >
                  <span className="era-item__title">{title}</span>
                  <span className="era-item__meta">{event.date_display || formatYear(event.date_start)}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Key Persons */}
      {detail.persons && detail.persons.length > 0 && (
        <div className="era-detail__section">
          <div className="era-detail__section-title">{t('trismegistos.era.keyPersons')}</div>
          <div className="era-detail__items">
            {detail.persons.slice(0, 5).map((person) => {
              const name = getLocalizedText(person, 'name', preferredLanguage)
              return (
                <button
                  key={person.id}
                  className="era-item"
                  onClick={() => onPersonClick(person.id)}
                >
                  <span className="era-item__title">{name}</span>
                  <span className="era-item__meta">{person.date_display || ''}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Related Shifts */}
      {relatedShifts && relatedShifts.length > 0 && (
        <div className="era-detail__section">
          <div className="era-detail__section-title">{t('trismegistos.era.relatedShifts')}</div>
          <div className="era-detail__items">
            {relatedShifts.map((shift) => {
              const title = getLocalizedText(shift, 'title', preferredLanguage)
              return (
                <button
                  key={shift.id}
                  className="era-item era-item--shift"
                  onClick={() => onShiftClick(shift.id)}
                >
                  <span className="era-item__icon">{'\u25B6'}</span>
                  <span className="era-item__title">{title}</span>
                  <span className="era-item__meta">{shift.page_count}p</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Globe View Button */}
      <div className="era-detail__actions">
        <button
          className="portal-btn portal-btn--secondary"
          onClick={() => onGlobeView(periodStart)}
        >
          {t('trismegistos.era.globeView')} ({formatYear(periodStart)})
        </button>
      </div>
    </div>
  )
}
