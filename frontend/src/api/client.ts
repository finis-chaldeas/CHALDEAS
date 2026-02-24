import axios from 'axios'

// Production backend URL (fallback from env var)
const API_URL = import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'https://chaldeas-backend-951004107180.asia-northeast3.run.app' : 'http://localhost:8100')

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(
        `[API Error] ${error.response.status}: ${error.response.data?.detail || error.message}`
      )
    } else {
      console.error('[API Error] Network error:', error.message)
    }
    return Promise.reject(error)
  }
)

// API functions
export const eventsApi = {
  list: (params?: Record<string, unknown>) => api.get('/events', { params }),
  get: (id: number) => api.get(`/events/${id}`),
  getBySlug: (slug: string) => api.get(`/events/slug/${slug}`),
  getChildren: (id: number, params?: { limit?: number; include_nested?: boolean }) => api.get(`/events/${id}/children`, { params }),
  getRelationships: (id: number) => api.get(`/events/${id}/relationships`),
  getLocations: (id: number) => api.get(`/events/${id}/locations`),
}

export const personsApi = {
  list: (params?: Record<string, unknown>) => api.get('/persons', { params }),
  get: (id: number) => api.get(`/persons/${id}`),
  getNarrative: (id: number) => api.get(`/persons/${id}/narrative`),
  getFlow: (id: number) => api.get(`/persons/${id}/flow`),
  getEvents: (id: number) => api.get(`/persons/${id}/events`),
  getRelations: (id: number, params?: { limit?: number; min_strength?: number }) =>
    api.get(`/persons/${id}/relations`, { params }),
  getSources: (id: number, params?: { limit?: number; include_contexts?: boolean; max_contexts?: number }) =>
    api.get(`/persons/${id}/sources`, { params }),
  getProperties: (id: number) => api.get(`/persons/${id}/properties`),
}

export const sourcesApi = {
  list: (params?: { type?: string; limit?: number; offset?: number }) =>
    api.get('/sources', { params }),
  get: (id: number) => api.get(`/sources/${id}`),
  getPersons: (id: number, params?: { limit?: number; offset?: number; min_mentions?: number }) =>
    api.get(`/sources/${id}/persons`, { params }),
  getMentions: (id: number, params?: { entity_type?: string; limit?: number; offset?: number }) =>
    api.get(`/sources/${id}/mentions`, { params }),
  getWiki: (id: number) => api.get(`/sources/wiki/${id}`),
}

export const locationsApi = {
  list: (params?: Record<string, unknown>) => api.get('/locations', { params }),
  get: (id: number) => api.get(`/locations/${id}`),
  getEvents: (id: number, params?: Record<string, unknown>) =>
    api.get(`/locations/${id}/events`, { params }),
}

// Globe Node API (location node system)
export const nodesApi = {
  list: (params?: { year_start?: number; year_end?: number; zoom?: string; limit?: number }) =>
    api.get('/globe/nodes', { params }),
  getEvents: (locationId: number, params?: { year_start?: number; year_end?: number; limit?: number; offset?: number }) =>
    api.get(`/globe/nodes/${locationId}/events`, { params }),
}

// Smart Markers API (hero cards + cluster bubbles)
export const smartMarkersApi = {
  get: (params: { year_start: number; year_end: number; zoom: string; bounds?: string }) =>
    api.get('/globe/smart-markers', { params }),
}

export const searchApi = {
  search: (q: string, params?: Record<string, unknown>) =>
    api.get('/search', { params: { q, ...params } }),
  observeDateLocation: (params: {
    year: number
    latitude?: number
    longitude?: number
    radius_km?: number
  }) => api.get('/search/date-location', { params }),
}

export const chatApi = {
  query: (query: string, context?: Record<string, unknown>) =>
    api.post('/chat', { query, context }),
  observe: (query: string) => api.post('/chat/observe', { query }),
  // Agent-based intelligent query (api_key optional - falls back to BM25 if not provided)
  agent: (query: string, apiKey?: string, language: string = 'en') =>
    api.post('/chat/agent', { query, api_key: apiKey || undefined, language }),
}

// Story API (Person/Place/Arc Story)
export const storyApi = {
  getPersonStory: (personId: number, minStrength?: number) =>
    api.get(`/story/person/${personId}`, { params: minStrength ? { min_strength: minStrength } : undefined }),
  checkPersonStory: (personId: number) =>
    api.get(`/story/person/${personId}/check`),
}

// Featured Persons API (landing page)
export const featuredApi = {
  getPersons: (params?: { era?: string; limit?: number; offset?: number }) =>
    api.get('/featured/persons', { params }),
  getRandom: () => api.get('/featured/random'),
}

// Servants API (FGO ↔ Historical Figures)
export const servantsApi = {
  list: (params?: Record<string, unknown>) => api.get('/servants/', { params }),
  get: (fgoName: string) => api.get(`/servants/${encodeURIComponent(fgoName)}`),
  getByPerson: (personId: number) => api.get(`/servants/by-person/${personId}`),
  getStats: () => api.get('/servants/stats'),
}

// Feed API (unified importance-ranked events + persons)
export const feedApi = {
  get: (params?: Record<string, unknown>) => api.get('/feed', { params }),
}

// Timeline API (period-based narrative exploration)
export const timelineApi = {
  listPeriods: (params?: { era_id?: string; min_score?: number; limit?: number; offset?: number }) =>
    api.get('/timeline/periods', { params }),
  getPeriodDetail: (periodStart: number, params?: { event_limit?: number; person_limit?: number }) =>
    api.get(`/timeline/periods/${periodStart}`, { params }),
  getPeriodEvents: (periodStart: number, params?: { limit?: number; offset?: number; min_score?: number }) =>
    api.get(`/timeline/periods/${periodStart}/events`, { params }),
  getPeriodPersons: (periodStart: number, params?: { limit?: number; offset?: number; min_score?: number; domain?: string }) =>
    api.get(`/timeline/periods/${periodStart}/persons`, { params }),
  submitFeedback: (data: { target_type: string; target_id: number; feedback_type: string; description?: string; suggested_fix?: string }) =>
    api.post('/timeline/feedback', data),
}

// Histories API (authored historical essays)
export const historiesApi = {
  list: (params?: Record<string, unknown>) => api.get('/histories', { params }),
  get: (id: number) => api.get(`/histories/${id}`),
  create: (data: Record<string, unknown>) => api.post('/histories', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/histories/${id}`, data),
  delete: (id: number) => api.delete(`/histories/${id}`),
}

// Reports API
export const reportsApi = {
  submit: (data: { entity_type: string; entity_id: number; field_name?: string; report_type: string; reason: string; suggested_correction?: string }) =>
    api.post('/reports', data),
}

// Showcase/Archive API
export const showcaseApi = {
  // FGO content
  getSingularities: () => api.get('/showcases/fgo/singularities'),
  getLostbelts: () => api.get('/showcases/fgo/lostbelts'),
  getServants: () => api.get('/showcases/fgo/servants'),
  // Pan-Human History
  getHistory: () => api.get('/showcases/history'),
  getLiterature: () => api.get('/showcases/literature'),
  getMusic: () => api.get('/showcases/music'),
  // Generic
  getAll: (params?: { type?: string; limit?: number }) =>
    api.get('/showcases', { params }),
  getById: (id: string) => api.get(`/showcases/${id}`),
  getStats: () => api.get('/showcases/stats/summary'),
}
