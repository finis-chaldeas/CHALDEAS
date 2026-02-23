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
  onSourceClick?: (sourceId: number) => void
}

export function NarrativePanel({
  selectedEventId,
  selectedPersonId,
  onClose,
  onEventClick,
  onPersonClick,
  onSourceClick,
}: NarrativePanelProps) {
  const isOpen = selectedEventId !== null || selectedPersonId !== null

  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        right: 0,
        top: 0,
        bottom: '64px',
        width: '380px',
        zIndex: 40,
        background: '#0a1018ee',
        backdropFilter: 'blur(8px)',
        borderLeft: '1px solid var(--chaldea-border)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          zIndex: 10,
          width: '28px',
          height: '28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '4px',
          border: '1px solid var(--chaldea-border)',
          background: 'rgba(5, 8, 16, 0.9)',
          color: 'var(--chaldea-cyan)',
          fontSize: '14px',
          cursor: 'pointer',
        }}
      >
        {'\u2715'}
      </button>

      {selectedEventId && (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <EventNarrativeCard
            eventId={selectedEventId}
            onEventClick={onEventClick}
            onPersonClick={onPersonClick}
          />
        </div>
      )}
      {selectedPersonId && (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <PersonNarrativeCard
            personId={selectedPersonId}
            onEventClick={onEventClick}
            onPersonClick={onPersonClick}
            onSourceClick={onSourceClick}
          />
        </div>
      )}
    </div>
  )
}
