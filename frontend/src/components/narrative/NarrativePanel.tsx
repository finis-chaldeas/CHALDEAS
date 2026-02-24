/**
 * NarrativePanel - Unified wrapper that shows EventNarrativeCard or PersonNarrativeCard
 * based on what's selected. Always active as the sole detail panel.
 */

import { EventNarrativeCard } from './EventNarrativeCard'
import { PersonNarrativeCard } from './PersonNarrativeCard'

interface NarrativePanelProps {
  selectedEventId: number | null
  selectedPersonId: number | null
  onClose: () => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
  onLocationClick?: (locationId: number) => void
  onSourceClick?: (sourceId: number) => void
  onRayshift?: (mode: 'causal' | 'life' | 'hierarchy', entityId: number) => void
}

export function NarrativePanel({
  selectedEventId,
  selectedPersonId,
  onClose,
  onEventClick,
  onPersonClick,
  onLocationClick,
  onSourceClick,
  onRayshift,
}: NarrativePanelProps) {
  const isOpen = selectedEventId !== null || selectedPersonId !== null

  if (!isOpen) return null

  return (
    <div className="narrative-panel">
      {/* Close button */}
      <button onClick={onClose} className="narrative-panel-close">
        {'\u2715'}
      </button>

      {selectedEventId && (
        <div className="narrative-panel-body">
          <EventNarrativeCard
            eventId={selectedEventId}
            onEventClick={onEventClick}
            onPersonClick={onPersonClick}
            onLocationClick={onLocationClick}
            onSourceClick={onSourceClick}
            onRayshift={onRayshift ? (id) => onRayshift('causal', id) : undefined}
            onRayshiftHierarchy={onRayshift ? (id) => onRayshift('hierarchy', id) : undefined}
          />
        </div>
      )}
      {selectedPersonId && (
        <div className="narrative-panel-body">
          <PersonNarrativeCard
            personId={selectedPersonId}
            onEventClick={onEventClick}
            onPersonClick={onPersonClick}
            onSourceClick={onSourceClick}
            onRayshift={onRayshift ? (id) => onRayshift('life', id) : undefined}
          />
        </div>
      )}
    </div>
  )
}
