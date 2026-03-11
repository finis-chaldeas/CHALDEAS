import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'
import { timelineApi, portalApi } from '../../api/client'
import type { PeriodSummary, CollectionSummary } from '../../types'
import { PeriodCard } from './PeriodCard'
import { CollectionGrid } from './CollectionGrid'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift: (shiftId: number) => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
}

const ERA_CHIPS = [
  { key: 'all', i18nKey: 'trismegistos.era.all' },
  { key: 'ancient', i18nKey: 'trismegistos.era.ancient' },
  { key: 'classical', i18nKey: 'trismegistos.era.classical' },
  { key: 'late_classical', i18nKey: 'trismegistos.era.late_classical' },
  { key: 'medieval', i18nKey: 'trismegistos.era.medieval' },
  { key: 'early_modern', i18nKey: 'trismegistos.era.early_modern' },
  { key: 'modern', i18nKey: 'trismegistos.era.modern' },
] as const

// Map era keys to approximate year ranges for client-side filtering
// Also matches period.era_id from DB: ancient, classical, late_classical, medieval, early_modern, modern
const ERA_RANGES: Record<string, [number, number]> = {
  ancient: [-3000, -800],
  classical: [-800, 200],
  late_classical: [200, 600],
  medieval: [600, 1500],
  early_modern: [1500, 1800],
  modern: [1800, 2100],
}

export function EraExplorer({ onGlobeView, onOpenShift, onEventClick, onPersonClick }: Props) {
  const { t } = useTranslation()
  const eraContext = usePortalStore((s) => s.eraContext)
  const close = usePortalStore((s) => s.close)
  const suspend = usePortalStore((s) => s.suspend)

  const [selectedEra, setSelectedEra] = useState<string>(eraContext || 'all')
  const [expandedPeriod, setExpandedPeriod] = useState<number | null>(null)

  // Sync with cross-tab navigation context
  useEffect(() => {
    if (eraContext) {
      setSelectedEra(eraContext)
    }
  }, [eraContext])

  // Fetch all periods
  const { data: periodsData, isLoading: periodsLoading } = useQuery({
    queryKey: ['era-periods'],
    queryFn: async () => {
      const res = await timelineApi.listPeriods({ min_score: 70, limit: 300 })
      return (res.data?.items ?? res.data) as PeriodSummary[]
    },
    staleTime: 5 * 60 * 1000,
  })

  // Fetch collections
  const { data: collections } = useQuery<CollectionSummary[]>({
    queryKey: ['portal-collections'],
    queryFn: async () => {
      const res = await portalApi.listCollections()
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  // Filter periods by selected era (client-side)
  const filteredPeriods = (periodsData ?? []).filter((p) => {
    if (selectedEra === 'all') return true
    const range = ERA_RANGES[selectedEra]
    if (!range) return true
    // Period overlaps with era range
    return p.period_start < range[1] && p.period_end > range[0]
  }).sort((a, b) => a.period_start - b.period_start)

  const handleGlobeView = (year: number) => {
    suspend()
    onGlobeView({ year })
  }

  const handleShiftClick = (shiftId: number) => {
    close()
    onOpenShift(shiftId)
  }

  const handleEventClick = (eventId: number) => {
    if (onEventClick) {
      close()
      onEventClick(eventId)
    }
  }

  const handlePersonClick = (personId: number) => {
    if (onPersonClick) {
      close()
      onPersonClick(personId)
    }
  }

  return (
    <div className="era-container">
      {/* A. Era Chip Bar */}
      <div className="era-chip-bar">
        {ERA_CHIPS.map(({ key, i18nKey }) => (
          <button
            key={key}
            className={`portal-chip ${selectedEra === key ? 'portal-chip--active' : ''}`}
            onClick={() => { setSelectedEra(key); setExpandedPeriod(null) }}
          >
            {t(i18nKey)}
          </button>
        ))}
      </div>

      {/* B. Period Timeline */}
      <div className="portal-section">
        <div className="portal-section__title">{t('trismegistos.era.periodTimeline')}</div>
        {periodsLoading ? (
          <div>
            <div className="portal-skeleton" style={{ height: 60, marginBottom: 8 }} />
            <div className="portal-skeleton" style={{ height: 60, marginBottom: 8 }} />
            <div className="portal-skeleton" style={{ height: 60 }} />
          </div>
        ) : filteredPeriods.length === 0 ? (
          <div className="era-empty">{t('trismegistos.era.noPeriodsFound')}</div>
        ) : (
          <div className="era-period-list">
            {filteredPeriods.map((period) => (
              <PeriodCard
                key={period.period_start}
                period={period}
                isExpanded={expandedPeriod === period.period_start}
                onToggle={() =>
                  setExpandedPeriod(
                    expandedPeriod === period.period_start ? null : period.period_start
                  )
                }
                onGlobeView={handleGlobeView}
                onShiftClick={handleShiftClick}
                onEventClick={handleEventClick}
                onPersonClick={handlePersonClick}
              />
            ))}
          </div>
        )}
      </div>

      {/* C. Theme Collections */}
      {collections && collections.length > 0 && (
        <div className="portal-section">
          <div className="portal-section__title">{t('trismegistos.era.themeCollections')}</div>
          <CollectionGrid collections={collections} />
        </div>
      )}
    </div>
  )
}
