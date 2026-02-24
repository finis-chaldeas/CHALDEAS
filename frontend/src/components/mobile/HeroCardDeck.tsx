/**
 * HeroCardDeck - Horizontal scrollable hero card deck for mobile
 *
 * Shows top hero markers as tappable cards in a horizontal scroll.
 * Tapping a card flies the map to that location and opens the event detail.
 */
import { useQuery } from '@tanstack/react-query'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore, getZoomLevel } from '../../store/globeStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import { useDebounce } from '../../hooks/useDebounce'
import { smartMarkersApi } from '../../api/client'
import type { SmartMarkersResponse, HeroMarker } from '../../types'

interface HeroCardDeckProps {
  onEventClick: (eventId: number) => void
}

function formatYear(y?: number): string {
  if (y === undefined || y === null) return ''
  return y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
}

export function HeroCardDeck({ onEventClick }: HeroCardDeckProps) {
  const { currentYear } = useTimelineStore()
  const { cameraPosition } = useGlobeStore()
  const { preferredLanguage } = useSettingsStore()
  const debouncedYear = useDebounce(currentYear, 200)

  const zoomLevel = cameraPosition?.altitude
    ? getZoomLevel(cameraPosition.altitude)
    : 'cosmic'

  const { data: smartMarkers } = useQuery<SmartMarkersResponse>({
    queryKey: ['smart-markers-mobile', debouncedYear, zoomLevel],
    queryFn: async () => {
      const timeRange = zoomLevel === 'cosmic' ? 200
        : zoomLevel === 'continental' ? 100
        : zoomLevel === 'regional' ? 50 : 25
      const res = await smartMarkersApi.get({
        year_start: debouncedYear - timeRange,
        year_end: debouncedYear + timeRange,
        zoom: zoomLevel,
      })
      return res.data
    },
    staleTime: 15 * 1000,
  })

  const heroes = smartMarkers?.heroes || []

  if (heroes.length === 0) return null

  const handleCardClick = (hero: HeroMarker) => {
    // Fly to hero location on map
    const { flyToLocation } = useGlobeStore.getState()
    flyToLocation(hero.lat, hero.lng)
    // Open event detail
    onEventClick(hero.id)
  }

  return (
    <div className="hero-card-deck">
      {heroes.map((hero) => {
        const title = getLocalizedText(
          hero as unknown as Record<string, unknown>,
          'title',
          preferredLanguage
        ) || hero.title

        return (
          <div
            key={hero.id}
            className="hero-card-deck-item"
            onClick={() => handleCardClick(hero)}
          >
            <div className="hero-card-deck-title">{title}</div>
            <div className="hero-card-deck-year">{formatYear(hero.year)}</div>
            {hero.location_name && (
              <div className="hero-card-deck-location">{hero.location_name}</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
