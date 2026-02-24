import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { feedApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore, type ZoomLevel } from '../../store/globeStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { FeedItem } from '../../types'

type FeedTab = 'all' | 'event' | 'person'
type SortMode = 'importance' | 'time' | 'distance'

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function getTimeRangeForZoom(zoom: ZoomLevel): number {
  switch (zoom) {
    case 'cosmic': return 200
    case 'continental': return 100
    case 'regional': return 25
    case 'local': return 10
  }
}

function haversineDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

interface ViewportFeedProps {
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export default function ViewportFeed({ onEventClick, onPersonClick }: ViewportFeedProps) {
  const cameraPosition = useGlobeStore((s) => s.cameraPosition)
  const viewMode = useGlobeStore((s) => s.viewMode)
  const zoomLevel = useGlobeStore((s) => s.zoomLevel)
  const rayshiftSteps = useGlobeStore((s) => s.rayshiftSteps)
  const currentYear = useTimelineStore((s) => s.currentYear)
  const { preferredLanguage } = useSettingsStore()

  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<FeedTab>('all')
  const [sortMode, setSortMode] = useState<SortMode>('importance')

  const isGlobeMode = viewMode === 'globe'
  const timeRange = getTimeRangeForZoom(zoomLevel)

  const bounds = useMemo(() => {
    if (!cameraPosition) return null
    const latRange = (cameraPosition.altitude || 2) * 30
    const lngRange = latRange * 1.5
    return {
      lat_min: cameraPosition.lat - latRange / 2,
      lat_max: cameraPosition.lat + latRange / 2,
      lng_min: cameraPosition.lng - lngRange / 2,
      lng_max: cameraPosition.lng + lngRange / 2,
    }
  }, [cameraPosition])

  const yearStart = currentYear - timeRange
  const yearEnd = currentYear + timeRange

  // Round aggressively to avoid API spam on every tiny rotation
  const roundedLat = cameraPosition ? Math.round(cameraPosition.lat) : null
  const roundedLng = cameraPosition ? Math.round(cameraPosition.lng) : null
  const roundedAlt = cameraPosition ? Math.round(cameraPosition.altitude * 10) / 10 : null

  const { data: items, isLoading } = useQuery({
    queryKey: ['viewport-feed', roundedLat, roundedLng, roundedAlt, currentYear, timeRange],
    queryFn: () =>
      feedApi.get({
        lat_min: bounds?.lat_min, lat_max: bounds?.lat_max,
        lng_min: bounds?.lng_min, lng_max: bounds?.lng_max,
        year_start: yearStart, year_end: yearEnd, limit: 30,
      }),
    select: (res) => (res.data?.items ?? res.data) as FeedItem[],
    enabled: isGlobeMode && open && !!cameraPosition && !!bounds,
    staleTime: 30000,
    placeholderData: (prev) => prev,
  })

  // All hooks MUST be above any early return (Rules of Hooks)
  const feedItems = items ?? []
  const filteredItems = activeTab === 'all' ? feedItems : feedItems.filter((i) => i.type === activeTab)

  const sortedItems = useMemo(() => {
    const arr = [...filteredItems]
    switch (sortMode) {
      case 'importance':
        return arr.sort((a, b) => (b.importance || 0) - (a.importance || 0))
      case 'time':
        return arr.sort((a, b) => (a.date_start ?? 0) - (b.date_start ?? 0))
      case 'distance':
        if (!cameraPosition) return arr
        return arr.sort((a, b) => {
          const dA = (a.latitude != null && a.longitude != null)
            ? haversineDistance(cameraPosition.lat, cameraPosition.lng, a.latitude, a.longitude)
            : Infinity
          const dB = (b.latitude != null && b.longitude != null)
            ? haversineDistance(cameraPosition.lat, cameraPosition.lng, b.latitude, b.longitude)
            : Infinity
          return dA - dB
        })
      default:
        return arr
    }
  }, [filteredItems, sortMode, cameraPosition])

  const eventCount = feedItems.filter((i) => i.type === 'event').length
  const personCount = feedItems.filter((i) => i.type === 'person').length
  const totalCount = eventCount + personCount

  // Hide when Rayshift is active (Rayshift bar replaces this)
  if (rayshiftSteps && rayshiftSteps.length > 0) return null
  if (!isGlobeMode) return null

  // Collapsed: small pill
  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="viewport-feed-pill">
        <span className="viewport-feed-pill-count">{totalCount}</span>
        <span className="viewport-feed-pill-label">in view</span>
      </button>
    )
  }

  const TABS: { key: FeedTab; label: string }[] = [
    { key: 'all', label: `All ${feedItems.length}` },
    { key: 'event', label: `Events ${eventCount}` },
    { key: 'person', label: `Figures ${personCount}` },
  ]

  const SORTS: { key: SortMode; label: string }[] = [
    { key: 'importance', label: 'Importance' },
    { key: 'time', label: 'Time' },
    { key: 'distance', label: 'Distance' },
  ]

  return (
    <div className="viewport-feed">
      {/* Header */}
      <div className="viewport-feed-header">
        <div className="viewport-feed-title-row">
          <span className="viewport-feed-title">In View</span>
          <button onClick={() => setOpen(false)} className="viewport-feed-close">
            {'\u2715'}
          </button>
        </div>
        <div className="viewport-feed-tabs">
          {TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`viewport-feed-tab ${activeTab === tab.key ? 'active' : ''}`}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sort */}
      <div className="viewport-feed-sort">
        {SORTS.map((s) => (
          <button key={s.key} onClick={() => setSortMode(s.key)}
            className={`viewport-feed-sort-btn ${sortMode === s.key ? 'active' : ''}`}>
            {s.label}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="viewport-feed-list">
        {isLoading ? (
          <div className="viewport-feed-empty">Loading...</div>
        ) : sortedItems.length === 0 ? (
          <div className="viewport-feed-empty">No items in view</div>
        ) : sortedItems.map((item) => (
          <button key={`${item.type}-${item.id}`}
            onClick={() => item.type === 'event' ? onEventClick(item.id) : onPersonClick(item.id)}
            className="viewport-feed-item">
            <div className="viewport-feed-item-header">
              <span className={`viewport-feed-item-type ${item.type}`}>
                {item.type}
              </span>
              {item.importance >= 4 && <span className="viewport-feed-item-star">{'\u2605'}</span>}
            </div>
            <div className="viewport-feed-item-title">
              {item.type === 'person'
                ? getLocalizedText(item as unknown as Record<string, unknown>, 'name', preferredLanguage) || item.name || item.title
                : getLocalizedText(item as unknown as Record<string, unknown>, 'title', preferredLanguage) || item.title}
            </div>
            {item.date_start != null && (
              <div className="viewport-feed-item-year">{formatYear(item.date_start)}</div>
            )}
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className="viewport-feed-footer">
        <span className="viewport-feed-range">
          {formatYear(yearStart)} {'\u2013'} {formatYear(yearEnd)}
        </span>
      </div>
    </div>
  )
}
