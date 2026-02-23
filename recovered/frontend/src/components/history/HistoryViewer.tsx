/**
 * HistoryViewer - Read-only panel for viewing a history essay
 *
 * - Renders entity tags [name](entity:type:id) as clickable links
 * - Shows featured entities and locations in header
 * - Right overlay panel (similar to EventDetailPanel)
 */
import { useQuery } from '@tanstack/react-query'
import { historiesApi } from '../../api/client'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { History } from '../../types'
import './history.css'

interface HistoryViewerProps {
  historyId: number
  onClose: () => void
  onPersonClick: (personId: number) => void
  onEventClick: (eventId: number) => void
  onLocationClick: (locationId: number) => void
  onEdit: (historyId: number) => void
}

const ENTITY_TAG_RE = /(\[[^\]]+\]\(entity:[^)]+\))/

function parseEntityTag(tag: string): { name: string; type: string; id: number } | null {
  const match = tag.match(/\[([^\]]+)\]\(entity:(person|event|location):(\d+)\)/)
  if (!match) return null
  return { name: match[1], type: match[2], id: parseInt(match[3], 10) }
}

function formatEra(start?: number, end?: number): string {
  if (start == null && end == null) return ''
  const fmt = (y: number) => y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
  if (start != null && end != null) return `${fmt(start)} ~ ${fmt(end)}`
  if (start != null) return `from ${fmt(start)}`
  return `until ${fmt(end!)}`
}

function RenderBody({ body, onEntityClick }: {
  body: string
  onEntityClick: (type: string, id: number) => void
}) {
  const parts = body.split(ENTITY_TAG_RE)

  return (
    <div className="history-body-text">
      {parts.map((part, i) => {
        const entity = parseEntityTag(part)
        if (entity) {
          return (
            <span
              key={i}
              className={`entity-tag entity-tag-${entity.type}`}
              onClick={() => onEntityClick(entity.type, entity.id)}
              role="button"
              tabIndex={0}
            >
              {entity.name}
            </span>
          )
        }
        // Render plain text with paragraph breaks
        return <span key={i}>{part}</span>
      })}
    </div>
  )
}

export function HistoryViewer({
  historyId,
  onClose,
  onPersonClick,
  onEventClick,
  onLocationClick,
  onEdit,
}: HistoryViewerProps) {
  const { preferredLanguage } = useSettingsStore()

  const { data: history, isLoading } = useQuery({
    queryKey: ['history-detail', historyId],
    queryFn: () => historiesApi.get(historyId),
    select: (res) => res.data as History,
  })

  const handleEntityClick = (type: string, id: number) => {
    if (type === 'person') onPersonClick(id)
    else if (type === 'event') onEventClick(id)
    else if (type === 'location') onLocationClick(id)
  }

  if (isLoading || !history) {
    return (
      <div className="history-viewer-overlay">
        <div className="history-viewer-panel">
          <div className="history-viewer-loading">Loading...</div>
        </div>
      </div>
    )
  }

  const featured = history.entities.filter(e => e.role === 'featured')
  const locations = history.entities.filter(e => e.role === 'location')
  const mentionCount = history.entities.filter(e => e.role === 'mentioned').length
  const era = formatEra(history.era_start, history.era_end)
  const historyRecord = history as unknown as Record<string, unknown>
  const title = getLocalizedText(historyRecord, 'title', preferredLanguage)
  const body = getLocalizedText(historyRecord, 'body', preferredLanguage) || history.body

  return (
    <div className="history-viewer-overlay">
      <div className="history-viewer-panel">
        {/* Header */}
        <div className="history-viewer-header">
          <button className="history-viewer-close" onClick={onClose}>{'\u2715'}</button>
          <button className="history-viewer-edit" onClick={() => onEdit(historyId)}>Edit</button>
        </div>

        {/* Title */}
        <div className="history-viewer-title">{title}</div>
        <div className="history-viewer-meta">
          {era && <span className="history-meta-era">{era}</span>}
          <span className="history-meta-category">{history.category}</span>
          <span className="history-meta-author">by {history.author_name || history.author_type}</span>
        </div>

        {/* Locations */}
        {locations.length > 0 && (
          <div className="history-viewer-locations">
            {'\uD83D\uDCCD'} {locations.map((loc, i) => (
              <span key={i}>
                <span
                  className="entity-tag entity-tag-location"
                  onClick={() => onLocationClick(loc.entity_id)}
                  role="button"
                  tabIndex={0}
                >
                  {loc.entity_name}
                </span>
                {i < locations.length - 1 && ', '}
              </span>
            ))}
          </div>
        )}

        {/* Featured entities */}
        {featured.length > 0 && (
          <div className="history-viewer-featured">
            {featured.map((e, i) => (
              <span
                key={i}
                className={`entity-chip entity-chip-${e.entity_type}`}
                onClick={() => handleEntityClick(e.entity_type, e.entity_id)}
                role="button"
                tabIndex={0}
              >
                {e.entity_type === 'person' ? '\u263E' : e.entity_type === 'event' ? '\u25CE' : '\uD83D\uDCCD'} {e.entity_name}
              </span>
            ))}
          </div>
        )}

        <div className="history-viewer-divider" />

        {/* Body */}
        <div className="history-viewer-body">
          <RenderBody body={body} onEntityClick={handleEntityClick} />
        </div>

        <div className="history-viewer-divider" />

        {/* Footer */}
        <div className="history-viewer-footer">
          {history.tags && history.tags.length > 0 && (
            <div className="history-tags">
              {history.tags.map((tag, i) => (
                <span key={i} className="history-tag">{tag}</span>
              ))}
            </div>
          )}
          <div className="history-mention-count">
            {mentionCount + featured.length} entities referenced
          </div>
        </div>
      </div>
    </div>
  )
}

export default HistoryViewer
