/**
 * LocationDetailView - FGO-style Location Detail with History
 *
 * Shows a location's information, historical events, and connected locations.
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import { ReportButton } from '../common'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { Event } from '../../types'
import './EntityDetailView.css'

interface LocationEvent {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  date_start: number | null
  date_end: number | null
}

interface LocationInfo {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  latitude?: number
  longitude?: number
  location_type?: string
  wikidata_id?: string
  parent_location_id?: number
  country?: string
  event_count?: number
  events?: LocationEvent[]
  details?: {
    description?: string
    description_ko?: string
    wikipedia_url?: string
  }
  names?: Array<{
    name: string
    language: string
    valid_from?: number
    valid_until?: number
  }>
  territories?: Array<{
    name: string
    name_ko?: string
    territory_type: string
    valid_from?: number
    valid_until?: number
  }>
}

interface Props {
  locationId: number
  onClose: () => void
  onEventClick: (event: Event) => void
  onLocationClick: (locationId: number) => void
}

export function LocationDetailView({ locationId, onClose, onEventClick, onLocationClick: _onLocationClick }: Props) {
  // Note: _onLocationClick reserved for future connected locations navigation
  void _onLocationClick
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()

  // Fetch location details from locations API
  const { data: location, isLoading: locationLoading } = useQuery<LocationInfo>({
    queryKey: ['location-detail', locationId],
    queryFn: async () => {
      const res = await api.get(`/locations/${locationId}`)
      return res.data
    },
  })

  // Use events from location API (primary_location_id based), sorted by date
  const historyEvents = useMemo(() => {
    if (!location?.events) return []
    return [...location.events]
      .sort((a, b) => (a.date_start || 0) - (b.date_start || 0))
  }, [location])

  // Calculate time span
  const timeSpan = useMemo(() => {
    if (historyEvents.length === 0) return null
    const years = historyEvents.filter(e => e.date_start !== null).map(e => e.date_start as number)
    if (years.length === 0) return null
    return {
      earliest: Math.min(...years),
      latest: Math.max(...years)
    }
  }, [historyEvents])

  const formatYear = (year: number | null | undefined) => {
    if (year === null || year === undefined) return '?'
    if (year < 0) return `${Math.abs(year)} BCE`
    return `${year} CE`
  }

  const handleEventClick = async (eventId: number) => {
    try {
      const res = await api.get(`/events/${eventId}`)
      if (res.data) {
        onEventClick(res.data)
      }
    } catch (err) {
      console.error('Failed to fetch event:', eventId, err)
    }
  }

  if (locationLoading) {
    return (
      <div className="entity-detail-view">
        <div className="entity-loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="entity-detail-view location-view">
      {/* Header */}
      <div className="entity-header">
        <button className="entity-close" onClick={onClose}>✕</button>
        <div className="entity-icon location">📍</div>
        <div className="entity-title-section">
          <h2 className="entity-name">{location ? getLocalizedText(location as unknown as Record<string, unknown>, 'name', preferredLanguage) || location.name : 'Unknown'}</h2>
        </div>
      </div>

      {/* Location Info */}
      <div className="entity-location-info">
        {location?.location_type && <div className="location-type">{location.location_type}</div>}
        {location?.country && <div className="location-type">{location.country}</div>}
      </div>

      {/* Description */}
      {location?.details?.description && (
        <div className="entity-section">
          <div className="entity-description">
            {getLocalizedText(location.details as unknown as Record<string, unknown>, 'description', preferredLanguage) || location.details.description}
          </div>
          {location.details.wikipedia_url && (
            <a href={location.details.wikipedia_url} target="_blank" rel="noopener noreferrer" className="entity-wiki-link">
              Wikipedia
            </a>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="entity-stats">
        <div className="stat-item">
          <span className="stat-value">{location?.event_count || historyEvents.length}</span>
          <span className="stat-label">{t('location.events')}</span>
        </div>
        {location?.names && location.names.length > 0 && (
          <div className="stat-item">
            <span className="stat-value">{location.names.length}</span>
            <span className="stat-label">{t('location.names')}</span>
          </div>
        )}
        {timeSpan && (
          <div className="stat-item span">
            <span className="stat-value">
              {formatYear(timeSpan.earliest)} ~ {formatYear(timeSpan.latest)}
            </span>
            <span className="stat-label">{t('location.timeSpan')}</span>
          </div>
        )}
      </div>

      {/* History Timeline — moved to top for visibility */}
      <div className="entity-section">
        <div className="section-header">
          <span className="section-icon">📜</span>
          <span className="section-title">{t('location.historyAtLocation')}</span>
        </div>
        <div className="timeline-list">
          {historyEvents.length > 0 ? (
            historyEvents.map((event, index) => (
              <div
                key={event.id}
                className="timeline-item"
                onClick={() => handleEventClick(event.id)}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="timeline-dot location" />
                <div className="timeline-year">{formatYear(event.date_start)}</div>
                <div className="timeline-title">{getLocalizedText(event as unknown as Record<string, unknown>, 'title', preferredLanguage) || event.title}</div>
              </div>
            ))
          ) : (
            <div className="timeline-empty">{t('location.noEvents')}</div>
          )}
        </div>
      </div>

      {/* Coordinates */}
      {(location?.latitude && location?.longitude) && (
        <div className="entity-coords">
          <span className="coords-icon">🌐</span>
          <span className="coords-value">
            {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
          </span>
        </div>
      )}

      {/* Historical Names */}
      {location?.names && location.names.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">🏷</span>
            <span className="section-title">{t('location.historicalNames')}</span>
          </div>
          <div className="timeline-list">
            {location.names
              .filter(n => n.valid_from || n.valid_until)
              .sort((a, b) => (a.valid_from || -9999) - (b.valid_from || -9999))
              .map((n, i) => (
                <div key={i} className="timeline-item" style={{ cursor: 'default' }}>
                  <div className="timeline-dot location" />
                  <div className="timeline-year">
                    {n.valid_from ? formatYear(n.valid_from) : '?'} ~ {n.valid_until ? formatYear(n.valid_until) : ''}
                  </div>
                  <div className="timeline-title">{n.name} <span style={{ opacity: 0.5, fontSize: '0.85em' }}>({n.language})</span></div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Territories */}
      {location?.territories && location.territories.length > 0 && (
        <div className="entity-section">
          <div className="section-header">
            <span className="section-icon">🏛</span>
            <span className="section-title">{t('location.politicalHistory')}</span>
          </div>
          <div className="timeline-list">
            {location.territories
              .sort((a, b) => (a.valid_from || -9999) - (b.valid_from || -9999))
              .map((t, i) => (
                <div key={i} className="timeline-item" style={{ cursor: 'default' }}>
                  <div className="timeline-dot" />
                  <div className="timeline-year">
                    {t.valid_from ? formatYear(t.valid_from) : '?'} ~ {t.valid_until ? formatYear(t.valid_until) : ''}
                  </div>
                  <div className="timeline-title">{getLocalizedText(t as unknown as Record<string, unknown>, 'name', preferredLanguage) || t.name} <span style={{ opacity: 0.5, fontSize: '0.85em' }}>({t.territory_type})</span></div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="entity-footer">
        <span className="entity-id">LOCATION #{locationId}</span>
        <ReportButton entityType="location" entityId={locationId} />
      </div>
    </div>
  )
}
