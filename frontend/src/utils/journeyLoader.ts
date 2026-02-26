import { eventsApi, personsApi, api } from '../api/client'
import type { HistoryShift, ShiftPage, EventRelationship, FlowEvent } from '../types'

type JourneyMode = 'causal' | 'life' | 'hierarchy'

interface RawStep {
  id: number
  title: string
  title_ko?: string
  year?: number
  lat?: number
  lng?: number
  description?: string
}

/** Fetch journey data and return as HistoryShift for unified rendering */
export async function loadJourney(mode: JourneyMode, entityId: number): Promise<HistoryShift | null> {
  let steps: RawStep[] = []
  let shiftTitle = ''
  let shiftTitleKo = ''

  if (mode === 'causal') {
    steps = await loadCausalSteps(entityId)
    const origin = steps.find((_, i) => i === Math.floor(steps.length / 2))
    shiftTitle = origin?.title ? `Causal Chain: ${origin.title}` : 'Causal Chain'
  } else if (mode === 'life') {
    steps = await loadLifeSteps(entityId)
    shiftTitle = steps[0]?.title ? `Life: ${steps[0].title}` : 'Life Journey'
  } else if (mode === 'hierarchy') {
    steps = await loadHierarchySteps(entityId)
    shiftTitle = steps[0]?.title || 'Story'
    shiftTitleKo = steps[0]?.title_ko || ''
  }

  if (steps.length === 0) return null

  const pages: ShiftPage[] = steps.map((s, i) => ({
    sequence_number: i,
    title: s.title,
    chapter_number: 1,
    page_narrative: s.description,
    year_start: s.year,
    lat: s.lat,
    lng: s.lng,
    event_id: s.id,
    importance: 3,
  }))

  const years = steps.filter(s => s.year != null).map(s => s.year!)

  return {
    id: -entityId, // synthetic ID
    chain_type: mode === 'causal' ? 'causal_chain' : mode === 'life' ? 'person_story' : 'aggregate',
    title: shiftTitle,
    title_ko: shiftTitleKo || undefined,
    year_start: years.length > 0 ? Math.min(...years) : 0,
    year_end: years.length > 0 ? Math.max(...years) : undefined,
    globe_importance: 5,
    chapter_count: 1,
    page_count: pages.length,
    pages,
  }
}

async function loadCausalSteps(entityId: number): Promise<RawStep[]> {
  const res = await eventsApi.getRelationships(entityId)
  const rels = (res.data?.relationships ?? []) as EventRelationship[]

  const causes = rels.filter(r => r.direction === 'incoming')
  const effects = rels.filter(r => r.direction === 'outgoing')

  const allIds = [...new Set([
    ...causes.map(r => r.related_event_id),
    entityId,
    ...effects.map(r => r.related_event_id),
  ])]
  const details = await Promise.all(
    allIds.map(id => eventsApi.get(id).then(r => r.data).catch(() => null))
  )
  const detailMap = new Map(details.filter(Boolean).map(d => [d.id, d]))

  const steps: RawStep[] = []

  const sortedCauses = [...causes].sort((a, b) => (a.related_event_date_start ?? 0) - (b.related_event_date_start ?? 0))
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

  const origin = detailMap.get(entityId)
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

  const sortedEffects = [...effects].sort((a, b) => (a.related_event_date_start ?? 0) - (b.related_event_date_start ?? 0))
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
}

async function loadLifeSteps(entityId: number): Promise<RawStep[]> {
  const res = await personsApi.getFlow(entityId)
  const flow = (res.data?.flow ?? []) as FlowEvent[]
  return flow.map(f => ({
    id: f.event_id,
    title: f.title,
    title_ko: f.title_ko,
    year: f.year,
    lat: f.lat,
    lng: f.lng,
    description: f.role,
  }))
}

async function loadHierarchySteps(entityId: number): Promise<RawStep[]> {
  const childRes = await eventsApi.getChildren(entityId)
  const children = (childRes.data?.items ?? childRes.data?.children ?? []) as Array<{
    id: number; title: string; date_start?: number
  }>

  const sorted = [...children].sort((a, b) => (a.date_start ?? 0) - (b.date_start ?? 0))

  interface EventDetail {
    id: number; title: string; title_ko?: string; date_start?: number; description?: string
    latitude?: number; longitude?: number; location?: { latitude?: number; longitude?: number }
  }
  const allIds = [entityId, ...sorted.map(c => c.id)]
  const details = await Promise.all(
    allIds.map(id => api.get(`/events/${id}`).then(r => r.data as EventDetail).catch(() => null))
  )
  const detailMap = new Map(details.filter((d): d is EventDetail => d !== null).map(d => [d.id, d]))

  const steps: RawStep[] = []
  const origin = detailMap.get(entityId)
  if (origin) {
    steps.push({
      id: origin.id,
      title: origin.title,
      title_ko: origin.title_ko,
      year: origin.date_start,
      lat: origin.latitude ?? origin.location?.latitude,
      lng: origin.longitude ?? origin.location?.longitude,
      description: origin.description,
    })
  }
  for (const child of sorted) {
    const d = detailMap.get(child.id)
    steps.push({
      id: child.id,
      title: child.title,
      title_ko: d?.title_ko,
      year: child.date_start,
      lat: d?.latitude ?? d?.location?.latitude,
      lng: d?.longitude ?? d?.location?.longitude,
      description: d?.description,
    })
  }
  return steps
}
