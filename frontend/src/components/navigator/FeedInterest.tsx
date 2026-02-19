/**
 * FeedInterest - "Netflix-style" simplified feed for Interest level
 *
 * Shows 3 curated episode cards + 5 highlights from current era.
 * Designed to hook users with compelling stories, not data dumps.
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, timelineApi } from '../../api/client'
import { SHEBA_EPISODES } from '../../data/shebaEpisodes'
import type { ShebaEpisode, TourStep } from '../../data/shebaEpisodes'
import { useObservationStore } from '../../store/observationStore'

interface FeedInterestProps {
  currentYear: number
  viewportBounds?: { north: number; south: number; east: number; west: number } | null
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onStartTour?: (episode: ShebaEpisode) => void
  onEventClick: (event: { id: number | string; title: string; date_start: number; importance: number; latitude?: number; longitude?: number }) => void
  onOpenTimeline?: () => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

// Map viewport center coordinates to a region name
function getRegionFromCoords(lat: number, lng: number): string | null {
  if (lat >= 35 && lat <= 72 && lng >= -10 && lng <= 40) return 'europe'
  if (lat >= 20 && lat <= 45 && lng >= 25 && lng <= 65) return 'near_east'
  if (lat >= 5 && lat <= 35 && lng >= 65 && lng <= 95) return 'south_asia'
  if (lat >= 15 && lat <= 55 && lng >= 95 && lng <= 145) return 'east_asia'
  if (lat >= -35 && lat <= 35 && lng >= -20 && lng <= 55) return 'africa'
  if (lat >= -55 && lat <= 70 && lng >= -170 && lng <= -30) return 'americas'
  return null
}

const REGION_LABELS: Record<string, string> = {
  europe: 'Europe',
  near_east: 'Near East',
  south_asia: 'South Asia',
  east_asia: 'East Asia',
  africa: 'Africa',
  americas: 'Americas',
}

// Map episode region string to observation region keys
const EPISODE_REGION_MAP: Record<string, string> = {
  'Greece': 'europe', 'Rome': 'europe', 'France': 'europe', 'England': 'europe',
  'Medieval Europe': 'europe', 'Europe': 'europe', 'Renaissance Europe': 'europe',
  'Persia': 'near_east', 'Mesopotamia': 'near_east', 'Near East': 'near_east',
  'Egypt': 'near_east', 'Ottoman': 'near_east',
  'India': 'south_asia', 'South Asia': 'south_asia',
  'China': 'east_asia', 'Japan': 'east_asia', 'East Asia': 'east_asia',
  'Africa': 'africa',
  'Americas': 'americas', 'North America': 'americas', 'South America': 'americas',
}

export function FeedInterest({
  currentYear,
  viewportBounds,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
  onEventClick,
  onOpenTimeline,
}: FeedInterestProps) {
  const [expandedEpisode, setExpandedEpisode] = useState<string | null>(null)
  const { recentViews, hasViewed, getTopRegion } = useObservationStore()
  const topRegion = getTopRegion()

  // Pick 5 episodes: weighted scoring based on observation history
  const recommendedEpisodes = useMemo(() => {
    const scored = SHEBA_EPISODES.map(ep => {
      const mid = (ep.dateRange.start + ep.dateRange.end) / 2
      const yearDistance = Math.abs(mid - currentYear) + 1

      // Year proximity score (0-1, closer = higher)
      const yearScore = 1 / (1 + yearDistance / 500)

      // Region match score
      const epRegionKey = EPISODE_REGION_MAP[ep.region] || null
      const regionScore = (epRegionKey && topRegion === epRegionKey) ? 1 : 0

      // Tour steps bonus
      const tourBonus = (ep.tourSteps && ep.tourSteps.length > 0) ? 1 : 0

      const totalScore = yearScore * 0.5 + regionScore * 0.3 + tourBonus * 0.2
      return { episode: ep, score: totalScore }
    })

    scored.sort((a, b) => b.score - a.score)
    return scored.slice(0, 5).map(s => s.episode)
  }, [currentYear, topRegion])

  // Fetch 5 highlights from current era (importance 5 only)
  const { data: highlights } = useQuery({
    queryKey: ['interest-highlights', Math.round(currentYear / 100) * 100],
    queryFn: () => api.get('/feed', {
      params: {
        year_start: currentYear - 200,
        year_end: currentYear + 200,
        limit: 5,
        min_importance: 5,
      }
    }),
    select: (res) => (res.data?.items || []).slice(0, 5),
  })

  // Context Banner data
  const periodStart = Math.floor(currentYear / 50) * 50
  const region = useMemo(() => {
    if (!viewportBounds) return null
    const centerLat = (viewportBounds.north + viewportBounds.south) / 2
    const centerLng = (viewportBounds.east + viewportBounds.west) / 2
    return getRegionFromCoords(centerLat, centerLng)
  }, [viewportBounds])

  const { data: periodData } = useQuery({
    queryKey: ['context-period-interest', periodStart],
    queryFn: () => timelineApi.getPeriodDetail(periodStart),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  })

  const handleEpisodeClick = (episode: ShebaEpisode) => {
    if (episode.tourSteps && episode.tourSteps.length > 0) {
      setExpandedEpisode(expandedEpisode === episode.id ? null : episode.id)
    } else {
      onFlyToLocation?.(episode.latitude, episode.longitude)
      onSetCurrentYear?.(episode.dateRange.start)
    }
  }

  const handleObserveStep = (step: TourStep) => {
    onFlyToLocation?.(step.latitude, step.longitude)
    onSetCurrentYear?.(step.year)
  }

  // Determine context headline
  const contextHeadline = useMemo(() => {
    if (!periodData) return null
    if (region && periodData.regions) {
      const regionData = periodData.regions.find(
        (r: { region: string; headline?: string }) => r.region === region
      )
      if (regionData?.headline) {
        return { headline: regionData.headline, regionLabel: REGION_LABELS[region] || region }
      }
    }
    if (periodData.headline) {
      return { headline: periodData.headline, regionLabel: '' }
    }
    return null
  }, [periodData, region])

  return (
    <div className="feed-interest">
      {/* Context Banner */}
      {contextHeadline && (
        <div className="context-banner">
          <div className="context-banner-label">NOW OBSERVING</div>
          <div className="context-banner-location">
            {contextHeadline.regionLabel && <span>{contextHeadline.regionLabel} {'\u00B7'} </span>}
            <span>{formatYear(currentYear)}</span>
          </div>
          <div className="context-banner-headline">{contextHeadline.headline}</div>
          {onOpenTimeline && (
            <button className="context-banner-link" onClick={onOpenTimeline}>
              View in Timeline {'\u2192'}
            </button>
          )}
        </div>
      )}

      {/* Recommended Episodes */}
      <div className="feed-interest-section">
        <div className="feed-interest-header">
          <span className="feed-interest-icon">{'\u25CE'}</span>
          <span>Recommended Observations</span>
        </div>

        <div className="feed-interest-episodes">
          {recommendedEpisodes.map(episode => (
            <div key={episode.id} className={`feed-interest-episode-wrapper ${expandedEpisode === episode.id ? 'expanded' : ''}`}>
              <button
                className="feed-interest-episode-card"
                onClick={() => handleEpisodeClick(episode)}
              >
                <div className="episode-card-top">
                  <span className="episode-card-region">{episode.region}</span>
                  <span className="episode-card-date">
                    {formatYear(episode.dateRange.start)}
                    {episode.dateRange.end !== episode.dateRange.start && ` ~ ${formatYear(episode.dateRange.end)}`}
                  </span>
                </div>
                <div className="episode-card-title">
                  {episode.title_ko || episode.title}
                </div>
                <div className="episode-card-desc">
                  {episode.description}
                </div>
                {episode.relatedServants && episode.relatedServants.length > 0 && (
                  <div className="episode-card-servants">
                    {'\u2726'} {episode.relatedServants.slice(0, 2).join(', ')}
                  </div>
                )}
                <div className="episode-card-action">
                  {episode.tourSteps
                    ? (expandedEpisode === episode.id ? '\u25B2 Collapse' : `\u25BC ${episode.tourSteps.length} Steps`)
                    : 'Observe \u2192'}
                </div>
              </button>

              {/* Expanded tour steps inline */}
              {expandedEpisode === episode.id && episode.tourSteps && (
                <div className="sheba-steps interest-steps">
                  <div className="sheba-steps-timeline">
                    {episode.tourSteps.map((step, i) => (
                      <div key={i} className="sheba-step">
                        <div className="sheba-step-dot" />
                        {i < episode.tourSteps!.length - 1 && <div className="sheba-step-line" />}
                        <div className="sheba-step-content">
                          <div className="sheba-step-year">{formatYear(step.year)}</div>
                          <div className="sheba-step-title">{step.title}</div>
                          <div className="sheba-step-desc">{step.description}</div>
                          <button
                            className="sheba-step-observe"
                            onClick={(e) => { e.stopPropagation(); handleObserveStep(step) }}
                          >
                            Observe {'\u2192'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  <button
                    className="sheba-start-tour-btn"
                    onClick={(e) => { e.stopPropagation(); onStartTour?.(episode) }}
                  >
                    {'\u25B6'} Start Guided Tour
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Observation-Based Recommendations */}
      {recentViews.length >= 3 && highlights && highlights.length > 0 && (
        <div className="feed-interest-section">
          <div className="feed-interest-header">
            <span className="feed-interest-icon">{'\u2605'}</span>
            <span>You might also enjoy</span>
          </div>
          {topRegion && (
            <div className="feed-interest-observation-hint">
              You&apos;ve explored {REGION_LABELS[topRegion] || topRegion} events frequently. Here are some you haven&apos;t seen:
            </div>
          )}
          <div className="feed-interest-highlights">
            {highlights
              .filter((item: { id: number; entity_type?: string }) =>
                !hasViewed(item.entity_type === 'person' ? 'person' : 'event', item.id)
              )
              .slice(0, 5)
              .map((item: { id: number; title: string; date_start?: number; importance?: number; latitude?: number; longitude?: number; entity_type?: string; name?: string }, i: number) => (
                <button
                  key={`${item.entity_type || 'event'}-${item.id}-${i}`}
                  className="feed-interest-highlight"
                  onClick={() => {
                    if (item.entity_type === 'event' || !item.entity_type) {
                      onEventClick({
                        id: item.id,
                        title: item.title || item.name || '',
                        date_start: item.date_start || currentYear,
                        importance: item.importance || 3,
                        latitude: item.latitude,
                        longitude: item.longitude,
                      })
                    }
                  }}
                >
                  <span className="highlight-star" style={{ color: '#ffd700' }}>{'\u2605'}</span>
                  <span className="highlight-title">{item.title || item.name}</span>
                  {item.date_start != null && (
                    <span className="highlight-year">{formatYear(item.date_start)}</span>
                  )}
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Era Highlights (shown when no observation history yet) */}
      {recentViews.length < 3 && highlights && highlights.length > 0 && (
        <div className="feed-interest-section">
          <div className="feed-interest-header">
            <span className="feed-interest-icon">{'\u2605'}</span>
            <span>This Era&apos;s Highlights</span>
          </div>

          <div className="feed-interest-highlights">
            {highlights.map((item: { id: number; title: string; date_start?: number; importance?: number; latitude?: number; longitude?: number; entity_type?: string; name?: string }, i: number) => (
              <button
                key={`${item.entity_type || 'event'}-${item.id}-${i}`}
                className="feed-interest-highlight"
                onClick={() => {
                  if (item.entity_type === 'event' || !item.entity_type) {
                    onEventClick({
                      id: item.id,
                      title: item.title || item.name || '',
                      date_start: item.date_start || currentYear,
                      importance: item.importance || 3,
                      latitude: item.latitude,
                      longitude: item.longitude,
                    })
                  }
                }}
              >
                <span className="highlight-star" style={{ color: '#ffd700' }}>{'\u2605'}</span>
                <span className="highlight-title">{item.title || item.name}</span>
                {item.date_start != null && (
                  <span className="highlight-year">{formatYear(item.date_start)}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mode hint */}
      <div className="feed-interest-hint">
        Want more details? Switch to Expert Mode below.
      </div>
    </div>
  )
}
