/**
 * EraTab - Historical periods/eras list
 */
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Event } from '../../types'

interface EraTabProps {
  onEventClick: (event: Event) => void
}

interface Period {
  id: number
  name: string
  name_ko?: string
  start_year: number
  end_year: number
  event_count?: number
}

// Fallback eras if API doesn't provide
const DEFAULT_ERAS = [
  { id: 1, name: 'Ancient', name_ko: '고대', start_year: -3000, end_year: 500, event_count: 0 },
  { id: 2, name: 'Medieval', name_ko: '중세', start_year: 500, end_year: 1500, event_count: 0 },
  { id: 3, name: 'Renaissance', name_ko: '르네상스', start_year: 1400, end_year: 1600, event_count: 0 },
  { id: 4, name: 'Early Modern', name_ko: '근세', start_year: 1500, end_year: 1800, event_count: 0 },
  { id: 5, name: 'Modern', name_ko: '근대', start_year: 1800, end_year: 1945, event_count: 0 },
  { id: 6, name: 'Contemporary', name_ko: '현대', start_year: 1945, end_year: 2025, event_count: 0 },
]

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function EraTab({ onEventClick }: EraTabProps) {
  const { t } = useTranslation()

  const { data, isLoading } = useQuery({
    queryKey: ['periods'],
    queryFn: () => api.get('/periods').catch(() => ({ data: { items: null } })),
    select: (res) => res.data,
    retry: false,
  })

  const periods: Period[] = data?.items || DEFAULT_ERAS

  const handleEraClick = async (era: Period) => {
    // Navigate to the middle of the era on the timeline
    const midYear = Math.floor((era.start_year + era.end_year) / 2)
    // Create a synthetic event to trigger timeline change
    onEventClick({
      id: 0,
      title: era.name,
      date_start: midYear,
      date_end: era.end_year,
      importance: 5,
    } as Event)
  }

  return (
    <div className="navigator-tab-content">
      <div className="navigator-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : (
          periods.map((era) => (
            <button
              key={era.id}
              className="navigator-item era-item"
              onClick={() => handleEraClick(era)}
            >
              <div className="navigator-item-icon">🏛️</div>
              <div className="navigator-item-content">
                <div className="navigator-item-title">{era.name}</div>
                <div className="navigator-item-meta">
                  {formatYear(era.start_year)} - {formatYear(era.end_year)}
                </div>
                {era.event_count !== undefined && era.event_count > 0 && (
                  <div className="navigator-item-count">
                    {era.event_count.toLocaleString()} events
                  </div>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
