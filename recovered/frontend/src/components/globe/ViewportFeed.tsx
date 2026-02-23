import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { feedApi } from '../../api/client'
import { useTimelineStore } from '../../store/timelineStore'
import { useGlobeStore, type ZoomLevel } from '../../store/globeStore'
import type { FeedItem } from '../../types'

type FeedTab = 'all' | 'event' | 'person'

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

interface ViewportFeedProps {
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

export default function ViewportFeed({ onEventClick, onPersonClick }: ViewportFeedProps) {
  const cameraPosition = useGlobeStore((s) => s.cameraPosition)
  const viewMode = useGlobeStore((s) => s.viewMode)
  const zoomLevel = useGlobeStore((s) => s.zoomLevel)
  const currentYear = useTimelineStore((s) => s.currentYear)

  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<FeedTab>('all')

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

  const roundedLat = cameraPosition ? Math.round(cameraPosition.lat * 10) / 10 : null
  const roundedLng = cameraPosition ? Math.round(cameraPosition.lng * 10) / 10 : null
  const roundedAlt = cameraPosition ? Math.round(cameraPosition.altitude * 100) / 100 : null

  const { data: items, isLoading } = useQuery({
    queryKey: ['viewport-feed', roundedLat, roundedLng, roundedAlt, currentYear, timeRange],
    queryFn: () =>
      feedApi.get({
        lat_min: bounds?.lat_min, lat_max: bounds?.lat_max,
        lng_min: bounds?.lng_min, lng_max: bounds?.lng_max,
        year_start: yearStart, year_end: yearEnd, limit: 30,
      }),
    select: (res) => (res.data?.items ?? res.data) as FeedItem[],
    enabled: isGlobeMode && !!cameraPosition && !!bounds,
    staleTime: 5000,
  })

  if (!isGlobeMode) return null

  const feedItems = items ?? []
  const filteredItems = activeTab === 'all' ? feedItems : feedItems.filter((i) => i.type === activeTab)
  const sortedItems = [...filteredItems].sort((a, b) => (b.importance || 0) - (a.importance || 0))
  const eventCount = feedItems.filter((i) => i.type === 'event').length
  const personCount = feedItems.filter((i) => i.type === 'person').length
  const totalCount = eventCount + personCount

  // Collapsed: small pill
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed left-3 top-12 z-20 flex items-center gap-1.5
                   bg-chaldea-panel/80 backdrop-blur-xl border border-chaldea-border/30
                   rounded-lg px-3 py-1.5 text-[10px] text-chaldea-text
                   hover:border-chaldea-cyan/20 transition-all"
      >
        <span className="text-chaldea-cyan font-semibold">{totalCount}</span>
        <span>in view</span>
      </button>
    )
  }

  const TABS: { key: FeedTab; label: string }[] = [
    { key: 'all', label: `All ${feedItems.length}` },
    { key: 'event', label: `Events ${eventCount}` },
    { key: 'person', label: `Figures ${personCount}` },
  ]

  return (
    <div className="fixed left-3 top-12 bottom-20 w-56 z-20 flex flex-col
                    bg-chaldea-panel/80 backdrop-blur-xl border border-chaldea-border/30
                    rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 border-b border-white/5 shrink-0">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[9px] text-chaldea-cyan uppercase tracking-widest font-semibold">In View</span>
          <button onClick={() => setOpen(false)}
            className="text-xs text-chaldea-text/50 hover:text-chaldea-text transition-colors leading-none">
            {'\u2715'}
          </button>
        </div>
        <div className="flex gap-px bg-white/5 rounded p-px">
          {TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`flex-1 text-[8px] font-semibold uppercase tracking-wide py-1 rounded transition-colors
                ${activeTab === tab.key
                  ? 'bg-chaldea-cyan/15 text-chaldea-cyan'
                  : 'text-chaldea-text/40 hover:text-chaldea-text/60'}`}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-1.5 py-1.5">
        {isLoading ? (
          <div className="text-[10px] text-chaldea-text/30 text-center py-8">Loading...</div>
        ) : sortedItems.length === 0 ? (
          <div className="text-[10px] text-chaldea-text/30 text-center py-8">No items in view</div>
        ) : sortedItems.map((item) => (
          <button key={`${item.type}-${item.id}`}
            onClick={() => item.type === 'event' ? onEventClick(item.id) : onPersonClick(item.id)}
            className="w-full text-left px-2 py-1.5 rounded border border-transparent
                       hover:bg-chaldea-cyan/5 hover:border-chaldea-border/30 transition-all block mb-0.5">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className={`text-[8px] uppercase font-semibold tracking-wide
                ${item.type === 'event' ? 'text-chaldea-cyan' : 'text-chaldea-orange'}`}>
                {item.type}
              </span>
              {item.importance >= 4 && <span className="text-[7px] text-chaldea-gold/50">{'\u2605'}</span>}
            </div>
            <div className="text-[11px] text-chaldea-text-bright leading-snug">
              {item.type === 'person' ? item.name || item.title : item.title}
            </div>
            {item.date_start != null && (
              <div className="text-[9px] text-chaldea-text/40 mt-0.5">{formatYear(item.date_start)}</div>
            )}
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-white/5 text-center">
        <span className="text-[8px] text-chaldea-text/30">
          {formatYear(yearStart)} {'\u2013'} {formatYear(yearEnd)}
        </span>
      </div>
    </div>
  )
}
