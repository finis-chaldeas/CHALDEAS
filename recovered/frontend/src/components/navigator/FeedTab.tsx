/**
 * FeedTab - Unified importance-ranked feed of events + persons
 *
 * Replaces the separate Events/Persons tabs with a single interleaved feed
 * sorted by importance. Card-based display with context strings.
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import { timelineApi } from '../../api/client'
import { SHEBA_EPISODES } from '../../data/shebaEpisodes'
import type { ShebaEpisode, TourStep } from '../../data/shebaEpisodes'
import { FeedInterest } from './FeedInterest'
import { useSettingsStore } from '../../store/settingsStore'
import type { FeedItem } from '../../types'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface FeedTabProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  onEventClick: (event: { id: number | string; title: string; date_start: number; importance: number; latitude?: number; longitude?: number }) => void
  onPersonClick: (personId: number) => void
  onOpenStory?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onStartTour?: (episode: ShebaEpisode) => void
  onOpenTimeline?: () => void
}

const TIME_RANGE = 50

function formatYear(year: number | undefined | null): string {
  if (year == null) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function getImportanceStars(importance: number): string {
  const filled = Math.min(importance, 5)
  const empty = 5 - filled
  return '\u2605'.repeat(filled) + '\u2606'.repeat(empty)
}

function getImportanceColor(importance: number): string {
  if (importance >= 5) return '#ffd700'
  if (importance >= 4) return '#00d4ff'
  if (importance >= 3) return '#8ba4b4'
  return '#4a5568'
}

function getCategoryColor(slug: string): string {
  const colors: Record<string, string> = {
    battle: '#ef4444',
    war: '#ef4444',
    politics: '#3b82f6',
    religion: '#a855f7',
    philosophy: '#ec4899',
    science: '#22c55e',
    culture: '#fbbf24',
    civilization: '#00d4ff',
    discovery: '#34d399',
  }
  return colors[slug] || '#6b7280'
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

function ContextBanner({
  currentYear,
  viewportBounds,
  onOpenTimeline,
}: {
  currentYear: number
  viewportBounds: ViewportBounds | null
  onOpenTimeline?: () => void
}) {
  // Round to 50-year period
  const periodStart = Math.floor(currentYear / 50) * 50

  // Get viewport center region
  const region = useMemo(() => {
    if (!viewportBounds) return null
    const centerLat = (viewportBounds.north + viewportBounds.south) / 2
    const centerLng = (viewportBounds.east + viewportBounds.west) / 2
    return getRegionFromCoords(centerLat, centerLng)
  }, [viewportBounds])

  const { data: periodData } = useQuery({
    queryKey: ['context-period', periodStart],
    queryFn: () => timelineApi.getPeriodDetail(periodStart),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  })

  if (!periodData) return null

  // Try to find region-specific headline, fallback to global
  let headline = periodData.headline
  let regionLabel = ''
  if (region && periodData.regions) {
    const regionData = periodData.regions.find(
      (r: { region: string; headline?: string }) => r.region === region
    )
    if (regionData?.headline) {
      headline = regionData.headline
      regionLabel = REGION_LABELS[region] || region
    }
  }

  if (!headline) return null

  return (
    <div className="context-banner">
      <div className="context-banner-label">NOW OBSERVING</div>
      <div className="context-banner-location">
        {regionLabel && <span>{regionLabel} {'\u00B7'} </span>}
        <span>{formatYear(currentYear)}</span>
      </div>
      <div className="context-banner-headline">{headline}</div>
      {onOpenTimeline && (
        <button className="context-banner-link" onClick={onOpenTimeline}>
          View in Timeline {'\u2192'}
        </button>
      )}
    </div>
  )
}

const INITIAL_EPISODES = 4

export function FeedTab({
  currentYear,
  viewportBounds,
  zoomLevel,
  onEventClick,
  onPersonClick,
  onOpenStory,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
  onOpenTimeline,
}: FeedTabProps) {
  const { experienceLevel } = useSettingsStore()

  // Interest level: simplified Netflix-style feed
  if (experienceLevel === 'interest') {
    return (
      <FeedInterest
        currentYear={currentYear}
        viewportBounds={viewportBounds}
        onFlyToLocation={onFlyToLocation}
        onSetCurrentYear={onSetCurrentYear}
        onStartTour={onStartTour}
        onEventClick={onEventClick}
        onOpenTimeline={onOpenTimeline}
      />
    )
  }

  // Expert level: full data feed (original behavior below)
  return (
    <FeedExpert
      currentYear={currentYear}
      viewportBounds={viewportBounds}
      zoomLevel={zoomLevel}
      onEventClick={onEventClick}
      onPersonClick={onPersonClick}
      onOpenStory={onOpenStory}
      onFlyToLocation={onFlyToLocation}
      onSetCurrentYear={onSetCurrentYear}
      onStartTour={onStartTour}
      onOpenTimeline={onOpenTimeline}
    />
  )
}

function EpisodeSteps({
  steps,
  onObserveStep,
  onStartTour,
}: {
  steps: TourStep[]
  onObserveStep: (step: TourStep) => void
  onStartTour: () => void
}) {
  return (
    <div className="sheba-steps">
      <div className="sheba-steps-timeline">
        {steps.map((step, i) => (
          <div key={i} className="sheba-step">
            <div className="sheba-step-dot" />
            {i < steps.length - 1 && <div className="sheba-step-line" />}
            <div className="sheba-step-content">
              <div className="sheba-step-year">{formatYear(step.year)}</div>
              <div className="sheba-step-title">{step.title}</div>
              <div className="sheba-step-desc">{step.description}</div>
              <button
                className="sheba-step-observe"
                onClick={(e) => { e.stopPropagation(); onObserveStep(step) }}
              >
                Observe {'\u2192'}
              </button>
            </div>
          </div>
        ))}
      </div>
      <button className="sheba-start-tour-btn" onClick={(e) => { e.stopPropagation(); onStartTour() }}>
        {'\u25B6'} Start Guided Tour
      </button>
    </div>
  )
}

function FeedExpert({
  currentYear,
  viewportBounds,
  zoomLevel,
  onEventClick,
  onPersonClick,
  onOpenStory,
  onFlyToLocation,
  onSetCurrentYear,
  onStartTour,
  onOpenTimeline,
}: FeedTabProps) {
  const [showAllEpisodes, setShowAllEpisodes] = useState(false)
  const [expandedEpisode, setExpandedEpisode] = useState<string | null>(null)
  const { t } = useTranslation()
  const debouncedYear = useDebounce(currentYear, 150)
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      year_start: debouncedYear - TIME_RANGE,
      year_end: debouncedYear + TIME_RANGE,
      limit: 40,
    }

    if (zoomLevel !== 'cosmic' && debouncedBounds) {
      params.lat_min = debouncedBounds.south
      params.lat_max = debouncedBounds.north
      params.lng_min = debouncedBounds.west
      params.lng_max = debouncedBounds.east
      params.limit = 60
    }

    return params
  }, [debouncedYear, zoomLevel, debouncedBounds])

  const { data: response, isLoading } = useQuery({
    queryKey: ['navigator-feed', queryParams],
    queryFn: () => api.get('/feed', { params: queryParams }),
    select: (res) => res.data,
  })

  const items: FeedItem[] = response?.items || []
  const eventsTotal: number = response?.events_total || 0
  const personsTotal: number = response?.persons_total || 0

  const visibleEpisodes = showAllEpisodes ? SHEBA_EPISODES : SHEBA_EPISODES.slice(0, INITIAL_EPISODES)

  const handleEpisodeClick = (episode: ShebaEpisode) => {
    if (episode.tourSteps && episode.tourSteps.length > 0) {
      setExpandedEpisode(expandedEpisode === episode.id ? null : episode.id)
    } else {
      if (onFlyToLocation) {
        onFlyToLocation(episode.latitude, episode.longitude)
      }
      if (onSetCurrentYear) {
        const midYear = Math.round((episode.dateRange.start + episode.dateRange.end) / 2)
        onSetCurrentYear(midYear)
      }
    }
  }

  const handleObserveStep = (step: TourStep) => {
    onFlyToLocation?.(step.latitude, step.longitude)
    onSetCurrentYear?.(step.year)
  }

  // Group feed items by year
  const groupedItems = useMemo(() => {
    if (items.length === 0) return []
    const groups: { year: number; items: FeedItem[] }[] = []
    let currentGroup: { year: number; items: FeedItem[] } | null = null

    for (const item of items) {
      const year = item.date_start ?? 0
      if (!currentGroup || currentGroup.year !== year) {
        currentGroup = { year, items: [] }
        groups.push(currentGroup)
      }
      currentGroup.items.push(item)
    }

    return groups
  }, [items])

  return (
    <div className="navigator-tab-content">
      {/* Context Banner */}
      <ContextBanner
        currentYear={currentYear}
        viewportBounds={viewportBounds}
        onOpenTimeline={onOpenTimeline}
      />

      {/* SHEBA Episodes Section */}
      <div className="sheba-section">
        <div className="sheba-header">
          <span className="sheba-title">{'\u25CE'} SHEBA: Curated Observations</span>
          {SHEBA_EPISODES.length > INITIAL_EPISODES && (
            <button
              className="sheba-expand-btn"
              onClick={() => setShowAllEpisodes(!showAllEpisodes)}
            >
              {showAllEpisodes ? 'Show less' : `+${SHEBA_EPISODES.length - INITIAL_EPISODES} more`}
            </button>
          )}
        </div>
        {visibleEpisodes.map(episode => (
          <div key={episode.id} className={`sheba-episode-wrapper ${expandedEpisode === episode.id ? 'expanded' : ''}`}>
            <button
              className="sheba-episode"
              onClick={() => handleEpisodeClick(episode)}
            >
              <div className="sheba-episode-bar" />
              <div className="sheba-episode-body">
                <div className="sheba-episode-title">{episode.title}</div>
                <div className="sheba-episode-desc">{episode.description}</div>
                <div className="sheba-episode-meta">
                  <span className="sheba-episode-year">
                    {formatYear(episode.dateRange.start)}
                    {episode.dateRange.end !== episode.dateRange.start && ` ~ ${formatYear(episode.dateRange.end)}`}
                  </span>
                  <span className="sheba-episode-region">{episode.region}</span>
                  {episode.relatedServants && episode.relatedServants.length > 0 && (
                    <span className="sheba-episode-servants">
                      {episode.relatedServants.slice(0, 2).map(s => (
                        <span key={s} className="timeline-servant-tag">{s}</span>
                      ))}
                    </span>
                  )}
                  {episode.tourSteps && episode.tourSteps.length > 0 ? (
                    <span className="sheba-expand-indicator">
                      {expandedEpisode === episode.id ? '\u25B2' : '\u25BC'} {episode.tourSteps.length} steps
                    </span>
                  ) : (
                    <span
                      className="sheba-observe-btn"
                      onClick={(e) => { e.stopPropagation(); handleEpisodeClick(episode) }}
                    >
                      Observe
                    </span>
                  )}
                </div>
              </div>
            </button>

            {/* Expanded tour steps */}
            {expandedEpisode === episode.id && episode.tourSteps && (
              <EpisodeSteps
                steps={episode.tourSteps}
                onObserveStep={handleObserveStep}
                onStartTour={() => onStartTour?.(episode)}
              />
            )}
          </div>
        ))}
      </div>

      {/* Result count */}
      <div className="nav-controls">
        <div className="nav-result-count">
          {items.length} items ({eventsTotal} events, {personsTotal} persons)
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* Feed list - grouped by year */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : items.length === 0 ? (
          <div className="navigator-empty">No notable items in this area/period</div>
        ) : (
          groupedItems.map((group) => (
            <div key={group.year} className="feed-year-group">
              <div className="feed-year-header">
                <span className="feed-year-label">{formatYear(group.year)}</span>
                <span className="feed-year-line" />
              </div>
              {group.items.map((item) => (
                item.type === 'event'
                  ? <EventCard key={`e-${item.id}`} item={item} onClick={onEventClick} />
                  : <PersonCard
                      key={`p-${item.id}`}
                      item={item}
                      onClick={onPersonClick}
                      onOpenStory={onOpenStory}
                    />
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function EventCard({
  item,
  onClick,
}: {
  item: FeedItem
  onClick: (event: { id: number | string; title: string; date_start: number; importance: number; latitude?: number; longitude?: number }) => void
}) {
  const imp = item.importance || 3
  const catSlug = item.category || 'general'
  const catName = item.category_name || catSlug

  return (
    <button
      className={`feed-card feed-card-event imp-${Math.min(imp, 5)}`}
      onClick={() => onClick({
        id: item.id,
        title: item.title,
        date_start: item.date_start || 0,
        importance: imp,
        latitude: item.latitude,
        longitude: item.longitude,
      })}
    >
      <div className="feed-card-imp-bar" style={{ backgroundColor: getImportanceColor(imp) }} />
      <div className="feed-card-body">
        {/* Stars + Category */}
        <div className="feed-card-top">
          <span className="feed-card-stars" style={{ color: getImportanceColor(imp) }}>
            {getImportanceStars(imp)}
          </span>
          <span
            className="feed-card-badge"
            style={{
              backgroundColor: getCategoryColor(catSlug) + '20',
              color: getCategoryColor(catSlug),
            }}
          >
            {catName}
          </span>
        </div>

        {/* Title */}
        <div className="feed-card-title">{item.title}</div>

        {/* Date + Location */}
        <div className="feed-card-meta">
          <span className="feed-card-year">{formatYear(item.date_start)}</span>
          {item.location_name && (
            <span className="feed-card-location">{item.location_name}</span>
          )}
        </div>

        {/* Description */}
        {item.description && (
          <div className="feed-card-desc">{item.description}</div>
        )}

        {/* Participants */}
        {item.participants && item.participants.length > 0 && (
          <div className="feed-card-participants">
            {item.participants.join(', ')}
            {(item.participant_count || 0) > item.participants.length && (
              <span className="feed-card-more">+{(item.participant_count || 0) - item.participants.length}</span>
            )}
          </div>
        )}
      </div>
    </button>
  )
}

function PersonCard({
  item,
  onClick,
  onOpenStory,
}: {
  item: FeedItem
  onClick: (personId: number) => void
  onOpenStory?: (personId: number) => void
}) {
  const imp = item.importance || 1

  return (
    <button
      className={`feed-card feed-card-person imp-${Math.min(imp, 5)}`}
      onClick={() => onClick(item.id)}
    >
      <div className="feed-card-imp-bar" style={{ backgroundColor: getImportanceColor(imp) }} />
      <div className="feed-card-body">
        {/* Stars + Role */}
        <div className="feed-card-top">
          <span className="feed-card-stars" style={{ color: getImportanceColor(imp) }}>
            {getImportanceStars(imp)}
          </span>
          {item.role && (
            <span className="feed-card-badge feed-card-badge-person">{item.role}</span>
          )}
        </div>

        {/* Name */}
        <div className="feed-card-title">{item.name || item.title}</div>

        {/* Lifespan + Birthplace */}
        <div className="feed-card-meta">
          <span className="feed-card-year">{item.date_display || formatYear(item.birth_year)}</span>
          {item.birthplace_name && (
            <span className="feed-card-location">{item.birthplace_name}</span>
          )}
        </div>

        {/* Biography snippet or context */}
        {item.biography ? (
          <div className="feed-card-desc">{item.biography}</div>
        ) : item.context ? (
          <div className="feed-card-context">{item.context}</div>
        ) : null}

        {/* Actions */}
        <div className="feed-card-actions">
          {item.event_count != null && item.event_count > 0 && (
            <span className="feed-card-events-badge">{item.event_count} events</span>
          )}
          {onOpenStory && (
            <span
              className="feed-card-story-btn"
              onClick={(e) => { e.stopPropagation(); onOpenStory(item.id) }}
              role="button"
              tabIndex={0}
            >
              Story
            </span>
          )}
        </div>
      </div>
    </button>
  )
}
