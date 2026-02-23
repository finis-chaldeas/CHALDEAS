import { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { eventsApi, personsApi } from '../../api/client'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import type { EventRelationship, FlowEvent } from '../../types'

type RayshiftMode = 'causal' | 'life' | 'tour'

interface RayshiftStep {
  id: number
  title: string
  year?: number
  lat?: number
  lng?: number
  description?: string
}

interface RayshiftProps {
  mode: RayshiftMode
  entityId: number
  onClose: () => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

function formatYear(year: number | undefined): string {
  if (year === undefined || year === null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export default function Rayshift({ mode, entityId, onClose, onEventClick }: RayshiftProps) {
  const flyToLocation = useGlobeStore((s) => s.flyToLocation)
  const setCurrentYear = useTimelineStore((s) => s.setCurrentYear)
  const [currentStep, setCurrentStep] = useState(0)

  // Fetch steps based on mode
  const { data: causalSteps } = useQuery({
    queryKey: ['rayshift-causal', entityId],
    queryFn: async () => {
      const res = await eventsApi.getRelationships(entityId)
      const rels = (res.data?.relationships ?? []) as EventRelationship[]
      // Build chain: entity itself + outgoing effects
      const steps: RayshiftStep[] = []
      // Fetch origin event
      const originRes = await eventsApi.get(entityId)
      const origin = originRes.data
      if (origin) {
        steps.push({
          id: origin.id as number,
          title: origin.title,
          year: origin.date_start,
          lat: origin.latitude ?? origin.location?.latitude,
          lng: origin.longitude ?? origin.location?.longitude,
          description: origin.description,
        })
      }
      // Add related events (causes first, then effects)
      const causes = rels.filter(r => r.direction === 'incoming')
      const effects = rels.filter(r => r.direction === 'outgoing')
      for (const r of [...causes, ...effects]) {
        steps.push({
          id: r.related_event_id,
          title: r.related_event_title,
          year: r.related_event_date_start,
          description: r.description,
        })
      }
      return steps
    },
    enabled: mode === 'causal',
  })

  const { data: lifeSteps } = useQuery({
    queryKey: ['rayshift-life', entityId],
    queryFn: async () => {
      const res = await personsApi.getFlow(entityId)
      const flow = (res.data?.flow ?? []) as FlowEvent[]
      return flow.map((f): RayshiftStep => ({
        id: f.event_id,
        title: f.title,
        year: f.year,
        lat: f.lat,
        lng: f.lng,
        description: f.role,
      }))
    },
    enabled: mode === 'life',
  })

  const steps = mode === 'causal' ? causalSteps : mode === 'life' ? lifeSteps : []

  // Navigate to current step
  const navigateToStep = useCallback((step: RayshiftStep) => {
    if (step.lat && step.lng) {
      flyToLocation(step.lat, step.lng)
    }
    if (step.year) {
      setCurrentYear(step.year)
    }
    if (mode === 'causal' || mode === 'tour') {
      onEventClick(step.id)
    } else if (mode === 'life') {
      onEventClick(step.id)
    }
  }, [flyToLocation, setCurrentYear, onEventClick, mode])

  // Navigate on step change
  useEffect(() => {
    if (steps && steps.length > 0 && currentStep < steps.length) {
      navigateToStep(steps[currentStep])
    }
  }, [currentStep, steps, navigateToStep])

  const goPrev = () => setCurrentStep((s) => Math.max(0, s - 1))
  const goNext = () => setCurrentStep((s) => Math.min((steps?.length || 1) - 1, s + 1))

  if (!steps || steps.length === 0) {
    return (
      <div className="rayshift-bar">
        <span className="rayshift-loading">Loading journey...</span>
        <button onClick={onClose} className="rayshift-close">{'\u2715'}</button>
      </div>
    )
  }

  const step = steps[currentStep]
  const modeLabel = mode === 'causal' ? 'Causal Chain' : mode === 'life' ? 'Life Journey' : 'Guided Tour'

  return (
    <div className="rayshift-bar">
      <div className="rayshift-mode">{modeLabel}</div>

      <button
        onClick={goPrev}
        disabled={currentStep === 0}
        className="rayshift-nav-btn"
      >
        &larr; Prev
      </button>

      <div className="rayshift-current">
        <span className="rayshift-title">{step.title}</span>
        <span className="rayshift-meta">
          {step.year ? formatYear(step.year) : ''} ({currentStep + 1}/{steps.length})
        </span>
      </div>

      <button
        onClick={goNext}
        disabled={currentStep === steps.length - 1}
        className="rayshift-nav-btn"
      >
        Next &rarr;
      </button>

      <button onClick={onClose} className="rayshift-close">{'\u2715'}</button>

      <style>{`
        .rayshift-bar {
          position: fixed;
          bottom: 70px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 60;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 16px;
          background: rgba(10, 14, 23, 0.95);
          border: 1px solid rgba(0, 212, 255, 0.3);
          border-radius: 8px;
          backdrop-filter: blur(12px);
          max-width: 90vw;
        }

        .rayshift-mode {
          font-size: 9px;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #fbbf24;
          font-weight: 600;
          white-space: nowrap;
        }

        .rayshift-nav-btn {
          padding: 4px 10px;
          border: 1px solid rgba(0, 212, 255, 0.3);
          border-radius: 4px;
          background: transparent;
          color: #00d4ff;
          font-size: 11px;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }

        .rayshift-nav-btn:hover:not(:disabled) {
          background: rgba(0, 212, 255, 0.15);
        }

        .rayshift-nav-btn:disabled {
          opacity: 0.3;
          cursor: default;
        }

        .rayshift-current {
          display: flex;
          flex-direction: column;
          align-items: center;
          min-width: 120px;
          max-width: 300px;
        }

        .rayshift-title {
          font-size: 12px;
          color: #d0e8f0;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 100%;
        }

        .rayshift-meta {
          font-size: 9px;
          color: #8ba4b4;
        }

        .rayshift-close {
          padding: 4px 8px;
          border: 1px solid rgba(255, 51, 102, 0.3);
          border-radius: 4px;
          background: transparent;
          color: #ff3366;
          font-size: 12px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .rayshift-close:hover {
          background: rgba(255, 51, 102, 0.15);
        }

        .rayshift-loading {
          font-size: 11px;
          color: #8ba4b4;
        }
      `}</style>
    </div>
  )
}
