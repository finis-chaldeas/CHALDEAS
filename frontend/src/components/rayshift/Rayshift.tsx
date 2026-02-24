import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { eventsApi, personsApi, api } from '../../api/client'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { EventRelationship, FlowEvent } from '../../types'

type RayshiftMode = 'causal' | 'life' | 'tour' | 'hierarchy'

interface RayshiftStep {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  year?: number
  lat?: number
  lng?: number
  description?: string
  isCurrent?: boolean
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
  const setRayshiftSteps = useGlobeStore((s) => s.setRayshiftSteps)
  const clearRayshiftSteps = useGlobeStore((s) => s.clearRayshiftSteps)
  const setCurrentYear = useTimelineStore((s) => s.setCurrentYear)
  const { preferredLanguage } = useSettingsStore()
  const [currentStep, setCurrentStep] = useState(0)

  // Stable ref for onEventClick to prevent infinite loop
  const onEventClickRef = useRef(onEventClick)
  onEventClickRef.current = onEventClick

  // Track if initial position has been set
  const initialized = useRef(false)

  // ─── Causal Chain ─────────────────────────────────────
  const { data: causalSteps } = useQuery({
    queryKey: ['rayshift-causal', entityId],
    queryFn: async () => {
      const res = await eventsApi.getRelationships(entityId)
      const rels = (res.data?.relationships ?? []) as EventRelationship[]

      const causes = rels.filter(r => r.direction === 'incoming')
      const effects = rels.filter(r => r.direction === 'outgoing')

      // Fetch all event details in parallel for location data
      const allIds = [
        ...causes.map(r => r.related_event_id),
        entityId,
        ...effects.map(r => r.related_event_id),
      ]
      const uniqueIds = [...new Set(allIds)]
      const details = await Promise.all(
        uniqueIds.map(id => eventsApi.get(id).then(r => r.data).catch(() => null))
      )
      const detailMap = new Map(details.filter(Boolean).map(d => [d.id, d]))

      // Build steps: causes (chronological) → origin → effects (chronological)
      const steps: RayshiftStep[] = []

      const sortedCauses = [...causes].sort(
        (a, b) => (a.related_event_date_start ?? 0) - (b.related_event_date_start ?? 0)
      )
      for (const r of sortedCauses) {
        const d = detailMap.get(r.related_event_id)
        steps.push({
          id: r.related_event_id,
          title: r.related_event_title,
          year: r.related_event_date_start,
          lat: d?.latitude ?? d?.location?.latitude,
          lng: d?.longitude ?? d?.location?.longitude,
          description: r.description,
        })
      }

      // Origin event
      const origin = detailMap.get(entityId)
      if (origin) {
        steps.push({
          id: origin.id as number,
          title: origin.title,
          year: origin.date_start,
          lat: origin.latitude ?? origin.location?.latitude,
          lng: origin.longitude ?? origin.location?.longitude,
          description: origin.description,
          isCurrent: true,
        })
      }

      const sortedEffects = [...effects].sort(
        (a, b) => (a.related_event_date_start ?? 0) - (b.related_event_date_start ?? 0)
      )
      for (const r of sortedEffects) {
        const d = detailMap.get(r.related_event_id)
        steps.push({
          id: r.related_event_id,
          title: r.related_event_title,
          year: r.related_event_date_start,
          lat: d?.latitude ?? d?.location?.latitude,
          lng: d?.longitude ?? d?.location?.longitude,
          description: r.description,
        })
      }

      return steps
    },
    enabled: mode === 'causal',
  })

  // ─── Life Journey ─────────────────────────────────────
  const { data: lifeSteps } = useQuery({
    queryKey: ['rayshift-life', entityId],
    queryFn: async () => {
      const res = await personsApi.getFlow(entityId)
      const flow = (res.data?.flow ?? []) as FlowEvent[]
      return flow.map((f): RayshiftStep => ({
        id: f.event_id,
        title: f.title,
        title_ko: f.title_ko,
        title_ja: f.title_ja,
        year: f.year,
        lat: f.lat,
        lng: f.lng,
        description: f.role,
      }))
    },
    enabled: mode === 'life',
  })

  // ─── Hierarchy (sub-events of a parent) ──────────────────
  const { data: hierarchySteps } = useQuery({
    queryKey: ['rayshift-hierarchy', entityId],
    queryFn: async () => {
      // Fetch children of this event
      const childRes = await eventsApi.getChildren(entityId)
      const children = (childRes.data?.items ?? childRes.data?.children ?? []) as Array<{
        id: number; title: string; date_start?: number; child_count?: number
      }>

      // Sort chronologically
      const sorted = [...children].sort((a, b) => (a.date_start ?? 0) - (b.date_start ?? 0))

      // Fetch parent event detail + all children details in parallel for locations
      interface EventDetail {
        id: number; title: string; title_ko?: string; title_ja?: string; date_start?: number; description?: string
        latitude?: number; longitude?: number; location?: { latitude?: number; longitude?: number }
      }
      const allIds = [entityId, ...sorted.map(c => c.id)]
      const details = await Promise.all(
        allIds.map(id => api.get(`/events/${id}`).then(r => r.data as EventDetail).catch(() => null))
      )
      const detailMap = new Map(details.filter((d): d is EventDetail => d !== null).map(d => [d.id, d]))

      // Build steps: parent (origin) first, then children chronologically
      const steps: RayshiftStep[] = []
      const origin = detailMap.get(entityId)
      if (origin) {
        steps.push({
          id: origin.id as number,
          title: origin.title,
          title_ko: origin.title_ko,
          title_ja: origin.title_ja,
          year: origin.date_start,
          lat: origin.latitude ?? origin.location?.latitude,
          lng: origin.longitude ?? origin.location?.longitude,
          description: origin.description,
          isCurrent: true,
        })
      }
      for (const child of sorted) {
        const d = detailMap.get(child.id)
        steps.push({
          id: child.id,
          title: child.title,
          title_ko: d?.title_ko,
          title_ja: d?.title_ja,
          year: child.date_start,
          lat: d?.latitude ?? d?.location?.latitude,
          lng: d?.longitude ?? d?.location?.longitude,
          description: d?.description,
        })
      }
      return steps
    },
    enabled: mode === 'hierarchy',
  })

  const steps = mode === 'causal' ? causalSteps : mode === 'life' ? lifeSteps : mode === 'hierarchy' ? hierarchySteps : []

  // Initialize: set currentStep to origin event index (don't navigate — user is already there)
  useEffect(() => {
    if (!initialized.current && steps && steps.length > 0) {
      initialized.current = true
      const originIdx = steps.findIndex(s => s.id === entityId)
      if (originIdx >= 0) setCurrentStep(originIdx)
    }
  }, [steps, entityId])

  // Sync steps to globe store for visual overlay (markers + arcs)
  useEffect(() => {
    if (steps && steps.length > 0) {
      const globeSteps = steps
        .filter(s => s.lat != null && s.lng != null)
        .map(s => ({ lat: s.lat!, lng: s.lng!, label: s.title }))
      if (globeSteps.length > 0) setRayshiftSteps(globeSteps)
    }
    return () => { clearRayshiftSteps() }
  }, [steps, setRayshiftSteps, clearRayshiftSteps])

  // Navigate to a step: fly camera + set year + open card
  const navigateToStep = useCallback(async (step: RayshiftStep) => {
    if (step.year) {
      setCurrentYear(step.year)
    }
    if (step.lat != null && step.lng != null) {
      flyToLocation(step.lat, step.lng)
    }
    onEventClickRef.current(step.id)
  }, [flyToLocation, setCurrentYear])

  // Prev/Next — navigate only on explicit user action
  const goPrev = () => {
    const next = Math.max(0, currentStep - 1)
    if (next !== currentStep && steps && next < steps.length) {
      setCurrentStep(next)
      navigateToStep(steps[next])
    }
  }

  const goNext = () => {
    const next = Math.min((steps?.length || 1) - 1, currentStep + 1)
    if (next !== currentStep && steps && next < steps.length) {
      setCurrentStep(next)
      navigateToStep(steps[next])
    }
  }

  if (!steps || steps.length === 0) {
    return (
      <div className="rayshift-bar">
        <span className="rayshift-loading">Loading journey...</span>
        <button onClick={onClose} className="rayshift-close">{'\u2715'}</button>
      </div>
    )
  }

  const step = steps[currentStep]
  const modeLabel = mode === 'causal' ? 'Causal Chain' : mode === 'life' ? 'Life Journey' : mode === 'hierarchy' ? 'Story Journey' : 'Guided Tour'

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
        <span className="rayshift-title">{getLocalizedText(step as unknown as Record<string, unknown>, 'title', preferredLanguage) || step.title}</span>
        <span className="rayshift-meta">
          {step.year ? formatYear(step.year) : ''} ({currentStep + 1}/{steps.length})
        </span>
      </div>

      {/* Step dots */}
      <div className="rayshift-dots">
        {steps.map((s, i) => (
          <button
            key={s.id}
            className={`rayshift-dot ${i === currentStep ? 'active' : i < currentStep ? 'visited' : ''}`}
            onClick={() => {
              if (i !== currentStep) {
                setCurrentStep(i)
                navigateToStep(steps[i])
              }
            }}
            title={s.title}
          />
        ))}
      </div>

      <button
        onClick={goNext}
        disabled={currentStep === steps.length - 1}
        className="rayshift-nav-btn"
      >
        Next &rarr;
      </button>

      <button onClick={onClose} className="rayshift-close">{'\u2715'}</button>
    </div>
  )
}
