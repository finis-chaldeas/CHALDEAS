import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'
import { shiftsApi, timelineApi, featuredApi } from '../../api/client'
import type { HistoryShift, PeriodSummary } from '../../types'
import { MagazineShiftHero } from './MagazineShiftHero'
import { MagazineShiftRow } from './MagazineShiftRow'
import { MagazineSpotlight } from './MagazineSpotlight'
import { MagazinePersonRow } from './MagazinePersonRow'
import { MagazineTypeGrid } from './MagazineTypeGrid'

interface GlobeViewOptions {
  year: number
  eventId?: number
}

interface Props {
  onGlobeView: (opts: GlobeViewOptions) => void
  onOpenShift: (shiftId: number) => void
  onPersonClick?: (personId: number) => void
}

const CHAIN_TYPES = ['aggregate', 'person_story', 'place_story', 'era_story', 'causal_chain'] as const
type ChainType = typeof CHAIN_TYPES[number]

export function HistoryMagazine({ onGlobeView, onOpenShift, onPersonClick }: Props) {
  const { t } = useTranslation()
  const close = usePortalStore((s) => s.close)
  const suspend = usePortalStore((s) => s.suspend)
  const navigateToEra = usePortalStore((s) => s.navigateToEra)
  // Fetch shifts (200 at once, client-side grouping)
  const { data: shiftData, isLoading: shiftsLoading } = useQuery({
    queryKey: ['magazine-shifts'],
    queryFn: async () => {
      const res = await shiftsApi.list({ limit: 200 })
      const data = res.data
      return (data?.items ?? data) as HistoryShift[]
    },
    staleTime: 5 * 60 * 1000,
  })

  // Fetch period narratives for spotlight
  const { data: periodData } = useQuery({
    queryKey: ['magazine-periods'],
    queryFn: async () => {
      const res = await timelineApi.listPeriods({ min_score: 80, limit: 100 })
      return (res.data?.items ?? res.data) as PeriodSummary[]
    },
    staleTime: 5 * 60 * 1000,
  })

  // Fetch featured persons
  const { data: personsData } = useQuery({
    queryKey: ['magazine-persons'],
    queryFn: async () => {
      const res = await featuredApi.getPersons({ limit: 10 })
      return res.data?.items ?? res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  const shifts = shiftData ?? []

  // Group shifts by chain_type
  const shiftGroups = useMemo(() => {
    const groups: Record<ChainType, HistoryShift[]> = {
      aggregate: [],
      person_story: [],
      place_story: [],
      era_story: [],
      causal_chain: [],
    }
    for (const s of shifts) {
      const type = s.chain_type as ChainType
      if (groups[type]) {
        groups[type].push(s)
      }
    }
    return groups
  }, [shifts])

  // Pick hero shift: highest page_count aggregate, or first shift
  const heroShift = useMemo(() => {
    const aggregates = shiftGroups.aggregate
    if (aggregates.length > 0) {
      return aggregates.reduce((best, s) => (s.page_count > best.page_count ? s : best), aggregates[0])
    }
    return shifts[0] || null
  }, [shiftGroups, shifts])

  // Pick 2 spotlight periods with narratives
  const spotlightPeriods = useMemo(() => {
    if (!periodData) return []
    return periodData.filter((p) => p.has_narrative).slice(0, 2)
  }, [periodData])

  // Type counts for quick links
  const typeCounts = useMemo(() => {
    return CHAIN_TYPES.map((type) => ({
      type,
      count: shiftGroups[type].length,
    }))
  }, [shiftGroups])

  const handleHeroStart = () => {
    if (heroShift) {
      close()
      onOpenShift(heroShift.id)
    }
  }

  const handleHeroGlobe = () => {
    if (heroShift) {
      suspend()
      onGlobeView({ year: heroShift.year_start })
    }
  }

  const handleShiftClick = (shiftId: number) => {
    close()
    onOpenShift(shiftId)
  }

  const handleSpotlightClick = (eraId: string) => {
    navigateToEra(eraId)
  }

  const handlePersonClick = (personId: number) => {
    if (onPersonClick) {
      close()
      onPersonClick(personId)
    }
  }

  const isLoading = shiftsLoading

  if (isLoading) {
    return (
      <div className="mag-loading">
        <div className="portal-skeleton" style={{ height: 180, marginBottom: 20 }} />
        <div className="portal-skeleton" style={{ height: 120, marginBottom: 20 }} />
        <div className="portal-skeleton" style={{ height: 80 }} />
      </div>
    )
  }

  return (
    <div className="mag-container">
      {/* A. Hero Shift */}
      {heroShift && (
        <MagazineShiftHero
          shift={heroShift}
          onStart={handleHeroStart}
          onGlobeView={handleHeroGlobe}
        />
      )}

      {/* B. Browse Shifts by Type */}
      <div className="portal-section">
        <div className="portal-section__title">{t('trismegistos.magazine.browseShifts')}</div>
        {CHAIN_TYPES.map((type) => {
          const group = shiftGroups[type]
          if (group.length === 0) return null
          return (
            <MagazineShiftRow
              key={type}
              chainType={type}
              shifts={group}
              onShiftClick={handleShiftClick}
            />
          )
        })}
      </div>

      {/* C. Era Spotlight */}
      {spotlightPeriods.length > 0 && (
        <div className="portal-section">
          <div className="portal-section__title">{t('trismegistos.magazine.eraSpotlight')}</div>
          <MagazineSpotlight
            periods={spotlightPeriods}
            onSpotlightClick={handleSpotlightClick}
          />
        </div>
      )}

      {/* D. Key Figures */}
      {personsData && personsData.length > 0 && (
        <div className="portal-section">
          <div className="portal-section__title">{t('trismegistos.magazine.keyFigures')}</div>
          <MagazinePersonRow
            persons={personsData}
            onPersonClick={handlePersonClick}
          />
        </div>
      )}

      {/* E. Type Quick Links */}
      <div className="portal-section">
        <div className="portal-section__title">{t('trismegistos.magazine.quickLinks')}</div>
        <MagazineTypeGrid typeCounts={typeCounts} />
      </div>
    </div>
  )
}
