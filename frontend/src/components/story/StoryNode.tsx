/**
 * StoryNode - Individual node in a story chain
 *
 * Displays:
 * - Node number/order
 * - Title and date
 * - Narrative text
 * - Location with map link
 * - Source citations
 */
import { useTranslation } from 'react-i18next'

export interface StoryNodeData {
  order: number
  title: string
  title_ko?: string
  year: number | null
  year_end?: number | null
  narrative: string
  narrative_ko?: string
  location?: {
    id: number
    name: string
    name_ko?: string
    latitude?: number
    longitude?: number
  }
  sources?: Array<{
    id: number
    title: string
    type: string
    url?: string
  }>
  event_id?: number
}

interface StoryNodeProps {
  node: StoryNodeData
  isActive?: boolean
  onClick?: () => void
  onLocationClick?: (locationId: number) => void
  onSourceClick?: (sourceId: number) => void
}

function formatYear(year: number | null, yearEnd?: number | null): string {
  if (year === null) return ''

  const formatSingle = (y: number) => {
    if (y < 0) return `${Math.abs(y)} BCE`
    return `${y} CE`
  }

  if (yearEnd && yearEnd !== year) {
    return `${formatSingle(year)} - ${formatSingle(yearEnd)}`
  }
  return formatSingle(year)
}

export function StoryNode({
  node,
  isActive = false,
  onClick,
  onLocationClick,
  onSourceClick
}: StoryNodeProps) {
  const { i18n } = useTranslation()
  const lang = i18n.language

  // Get localized content
  const title = (lang === 'ko' && node.title_ko) ? node.title_ko : node.title
  const narrative = (lang === 'ko' && node.narrative_ko) ? node.narrative_ko : node.narrative
  const locationName = node.location
    ? ((lang === 'ko' && node.location.name_ko) ? node.location.name_ko : node.location.name)
    : null

  return (
    <div
      className={`story-node ${isActive ? 'story-node-active' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header */}
      <div className="story-node-header">
        <span className="story-node-number">{node.order}</span>
        <span className="story-node-title">{title}</span>
        {node.year !== null && (
          <span className="story-node-date">
            {formatYear(node.year, node.year_end)}
          </span>
        )}
      </div>

      {/* Narrative */}
      <div className="story-node-narrative">
        {narrative}
      </div>

      {/* Meta: Location & Sources */}
      <div className="story-node-meta">
        {/* Location */}
        {node.location && (
          <button
            className="story-node-meta-item story-node-location"
            onClick={(e) => {
              e.stopPropagation()
              if (onLocationClick && node.location) {
                onLocationClick(node.location.id)
              }
            }}
          >
            <span className="meta-icon">📍</span>
            <span>{locationName}</span>
          </button>
        )}

        {/* Sources */}
        {node.sources && node.sources.length > 0 && (
          <div className="story-node-sources">
            <span className="meta-icon">📚</span>
            {node.sources.map((source, idx) => (
              <button
                key={source.id}
                className="story-node-source-link"
                onClick={(e) => {
                  e.stopPropagation()
                  if (onSourceClick) onSourceClick(source.id)
                }}
              >
                {source.title}
                {idx < node.sources!.length - 1 && ', '}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default StoryNode
