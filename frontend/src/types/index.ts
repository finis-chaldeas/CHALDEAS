// Core types for CHALDEAS frontend

export interface Category {
  id: number
  name: string
  name_ko?: string
  slug: string
  color: string
  icon?: string
  children?: Category[]
}

export interface Location {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  latitude: number
  longitude: number
  location_type: 'point' | 'natural' | 'sea'
  wikidata_id?: string
  parent_location_id?: number
  country?: string
  details?: LocationDetailInfo
  names?: LocationNameEntry[]
  territories?: TerritoryInfo[]
}

export interface LocationDetailInfo {
  description?: string
  description_ko?: string
  description_ja?: string
  description_source?: string
  description_source_url?: string
  wikipedia_url?: string
}

export interface LocationNameEntry {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  language: string
  is_primary: boolean
  valid_from?: number
  valid_until?: number
}

export interface TerritoryInfo {
  id: number
  name: string
  name_ko?: string
  territory_type: string
  founded_year?: number
  dissolved_year?: number
}

export interface TerritoryLocation {
  territory: TerritoryInfo
  valid_from?: number
  valid_until?: number
  relation_type: string
}

export interface EventDetailInfo {
  slug?: string
  description?: string
  description_ko?: string
  description_ja?: string
  description_source?: string
  description_source_url?: string
  image_url?: string
  wikipedia_url?: string
  date_start_month?: number
  date_start_day?: number
  date_end_month?: number
  date_end_day?: number
}

export interface Event {
  id: number | string
  title: string
  title_ko?: string
  wikidata_id?: string
  date_start: number // Negative for BCE
  date_end?: number
  date_display?: string // "490 BCE"
  date_precision?: 'exact' | 'year' | 'decade' | 'century'
  importance: number
  certainty?: string
  temporal_scale?: string
  category?: Category | string
  // Direct coordinates (from API)
  latitude?: number
  longitude?: number
  // Or nested location object
  location?: Location // Primary location
  locations?: LocationRole[]
  // Hierarchy
  parent_event_id?: number
  is_aggregate?: boolean
  hierarchy_level?: number      // 0=Era, 1=Mega, 2=Aggregate, 3=Major, 4=Minor
  aggregate_type?: string       // war, movement, dynasty, ...
  parent_status?: string
  child_count?: number          // computed
  // Relations
  persons?: PersonRole[]
  person_count?: number    // Total person count (from batch query in list API)
  sources?: SourceReference[]
  source_count?: number    // Total source count (from batch query in list API)
  // Details (from event_details, populated on detail view)
  details?: EventDetailInfo
  // Backward-compat fields (also populated from details by API)
  description?: string
  description_ko?: string
  wikipedia_url?: string
  image_url?: string
}

export interface LocationRole extends Location {
  role: 'location' | 'origin' | 'destination'
}

export interface PersonDetailInfo {
  slug?: string
  biography?: string
  biography_ko?: string
  biography_ja?: string
  biography_source?: string
  biography_source_url?: string
  image_url?: string
  wikipedia_url?: string
  birth_date_precision?: string
  death_date_precision?: string
  era?: string
}

export interface PersonNameEntry {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  language: string
  name_type: string
  is_primary: boolean
  valid_from?: number
  valid_until?: number
}

export interface Person {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  wikidata_id?: string
  birth_year?: number
  death_year?: number
  floruit_start?: number
  floruit_end?: number
  lifespan_display?: string
  role?: string
  certainty?: string
  birthplace?: Location
  deathplace?: Location
  details?: PersonDetailInfo
  names?: PersonNameEntry[]
}

export interface FlowEvent {
  event_id: number
  title: string
  title_ko?: string
  title_ja?: string
  year?: number
  year_end?: number
  location?: string
  lat?: number
  lng?: number
  role?: string
}

export interface PersonFlow {
  person_id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  birthplace?: { id: number; name: string; lat?: number; lng?: number }
  deathplace?: { id: number; name: string; lat?: number; lng?: number }
  flow: FlowEvent[]
  total_events: number
}

export interface PersonRole extends Person {
  role: string
}

export interface Source {
  id: number
  name: string
  title?: string
  type: string
  url?: string
  author?: string
  publication_year?: number
  description?: string
  reliability?: number
  archive_type?: string
  content?: string
}

export interface SourceReference extends Source {
  page_reference?: string
  quote?: string
}

// Person Sources (Books mentioning a person)
export interface MentionContext {
  mention_text: string
  context_text?: string
  confidence: number
  chunk_index?: number
}

export interface SourceWithMentions {
  id: number
  name: string
  title?: string
  type: string
  author?: string
  mention_count: number
  person_count: number
  mentions: MentionContext[]
}

export interface PersonSourceList {
  person_id: number
  sources: SourceWithMentions[]
  total: number
}

// Feed item (unified event/person card)
export interface FeedItem {
  type: 'event' | 'person'
  id: number
  title: string
  title_ko?: string
  date_start?: number
  date_end?: number
  date_display?: string
  importance: number
  connection_count?: number
  context?: string
  // Event-specific
  category?: string
  category_name?: string
  location_name?: string
  latitude?: number
  longitude?: number
  description?: string
  participants?: string[]
  participant_count?: number
  parent_event_id?: number
  // Person-specific
  name?: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
  biography?: string  // From person_details via feed API
  event_count?: number
  birthplace_name?: string
}

export interface FeedResponse {
  items: FeedItem[]
  events_total: number
  persons_total: number
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
}

export interface SearchResults {
  query: string
  results: {
    events: Event[]
    persons: Person[]
    locations: Location[]
  }
}

export interface ChatResponse {
  answer: string
  sources: Array<{
    source: Source
    relevance: number
    excerpt?: string
  }>
  confidence: number
  related_events: Event[]
  suggested_queries: string[]
}

// Agent Response Types
export type ResponseFormat =
  | 'narrative'
  | 'comparison_table'
  | 'timeline_list'
  | 'flow_chart'
  | 'map_markers'
  | 'cards'

export type QueryIntent =
  | 'comparison'
  | 'timeline'
  | 'causation'
  | 'deep_dive'
  | 'overview'
  | 'map_query'
  | 'person_info'
  | 'connection'

export interface AgentAnalysis {
  original_query: string
  english_query: string
  intent: QueryIntent
  intent_confidence: 'high' | 'medium' | 'low'
  entities: {
    events: string[]
    persons: string[]
    locations: string[]
    time_periods: Array<{ from?: number; to?: number; label?: string }>
    categories: string[]
    keywords: string[]
  }
  response_format: ResponseFormat
  search_strategy: string
  requires_multiple_searches: boolean
}

export interface AgentSearchResult {
  query_used: string
  filters_applied: Record<string, unknown>
  results: Array<{
    content_type: string
    content_id: number
    content_text: string
    metadata: Record<string, unknown>
    similarity: number
  }>
  result_count: number
}

export interface ComparisonItem {
  title: string
  date?: string
  key_points: string[]
}

export interface TimelineEvent {
  date: string
  title: string
  description: string
}

export interface CausalChain {
  cause: string
  effect: string
  explanation: string
}

export interface MapMarker {
  title: string
  lat: number
  lng: number
  description: string
}

export interface CardItem {
  title: string
  subtitle?: string
  content: string
  tags?: string[]
}

export interface AgentStructuredData {
  type: 'comparison' | 'timeline' | 'causation' | 'map' | 'cards'
  items?: ComparisonItem[]
  comparison_axes?: string[]
  events?: TimelineEvent[]
  chain?: CausalChain[]
  markers?: MapMarker[]
  cards?: CardItem[]
}

export interface AgentResponseData {
  intent: string
  format: ResponseFormat
  answer: string
  structured_data: AgentStructuredData
  sources: Array<{
    id: number
    title: string
    similarity: number
    date_start?: number
  }>
  confidence: number
  suggested_followups: string[]
  navigation?: {
    target_year?: number
    locations?: Array<{ lat: number; lng: number; title: string }>
  }
}

export interface AgentResponse {
  analysis: AgentAnalysis
  search_results: AgentSearchResult[]
  response: AgentResponseData
}

// History (authored essays with entity tagging)
export interface HistoryEntity {
  id: number
  entity_type: 'person' | 'event' | 'location'
  entity_id: number
  entity_name?: string
  role: 'featured' | 'mentioned' | 'location'
}

export interface History {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  summary?: string
  era_start?: number
  era_end?: number
  body: string
  body_ko?: string
  body_ja?: string
  category: string
  tags: string[]
  author_type: 'system' | 'user'
  author_name?: string
  importance: number
  status: string
  entities: HistoryEntity[]
  created_at: string
  updated_at: string
}

export interface HistoryListItem {
  id: number
  title: string
  title_ko?: string
  summary?: string
  era_start?: number
  era_end?: number
  category: string
  author_type: string
  author_name?: string
  importance: number
  status: string
  entity_count: number
  created_at: string
}

// Event Relationships (causal connections)
export interface EventRelationship {
  id: number
  relationship_type: string
  description?: string
  strength?: number
  certainty?: number
  related_event_id: number
  direction: 'incoming' | 'outgoing'
  related_event_title: string
  related_event_title_ko?: string
  related_event_title_ja?: string
  related_event_date_start?: number
  related_event_date_end?: number
}

// Event Hierarchy Node
export interface EventHierarchyNode {
  id: number
  title: string
  title_ko?: string
  date_start: number
  date_end?: number
  importance?: number
  child_count?: number
  children?: EventHierarchyNode[]
}

// Person Narrative (LLM-generated)
export interface PersonNarrative {
  person_id: number
  has_narrative: boolean
  narrative?: string
  significance?: string
  causes?: string
  consequences?: string
}

// Person Relations
export interface PersonRelation {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  strength: number
  time_distance?: number
  relationship_type?: string
  is_bidirectional?: number
}

// Person Source (from text_mentions)
export interface PersonSource {
  id: number
  name: string
  title?: string
  type: string
  author?: string
  mention_count: number
  person_count?: number
  mentions?: { mention_text: string; context_text?: string; confidence?: number; chunk_index?: number }[]
}

// Widget System (modular shift page components)
export type WidgetSlotPosition = 'left' | 'right' | 'bottom' | 'overlay'

export interface PageWidget {
  type: string
  slot: WidgetSlotPosition
  data: Record<string, unknown>
  priority?: number
}

// History Shift (page-based sequential narrative)
export interface HistoryShift {
  id: number
  chain_type: 'person_story' | 'place_story' | 'era_story' | 'causal_chain' | 'aggregate'
  title: string
  title_ko?: string
  title_ja?: string
  summary?: string
  summary_ko?: string
  summary_ja?: string
  year_start: number
  year_end?: number
  globe_importance: number
  chapter_count: number
  page_count: number
  display_type?: string
  thumbnail_url?: string
  status?: string
  parent_shift_id?: number
  pages: ShiftPage[]
}

export interface ShiftPage {
  sequence_number: number
  title?: string
  title_ko?: string
  title_ja?: string
  chapter_number: number
  chapter_title?: string
  page_narrative?: string
  page_narrative_ko?: string
  page_narrative_ja?: string
  narrative?: string
  narrative_ko?: string
  narrative_ja?: string
  year_start?: number
  year_end?: number
  lat?: number
  lng?: number
  event_id?: number
  person_id?: number
  location_id?: number
  location_name?: string
  location_name_ko?: string
  importance: number
  media_url?: string
  sub_shift_id?: number
  widgets?: PageWidget[] | null
  camera_altitude?: number
  highlight_locations?: Array<{
    lat: number
    lng: number
    label?: string
    label_ko?: string
    label_ja?: string
  }>
}

// Smart Markers (Globe hero cards + cluster bubbles)
export interface NearbyEvent {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  year?: number
  category?: string
  importance: number
  location_name?: string
  location_name_ko?: string
  location_name_ja?: string
  lat?: number
  lng?: number
}

export interface NearbyPerson {
  id: number
  name: string
  name_ko?: string
  name_ja?: string
  birth_year?: number
  death_year?: number
  role?: string
  importance: number
}

export interface HeroMarker {
  id: number
  type: 'event'
  lat: number
  lng: number
  title: string
  title_ko?: string
  title_ja?: string
  description?: string
  year?: number
  year_end?: number
  category?: string
  importance: number
  child_count: number
  location_name?: string
  location_name_ko?: string
  location_name_ja?: string
  location_id?: number
  nearby_events: NearbyEvent[]
  nearby_event_count: number
  nearby_persons: NearbyPerson[]
  nearby_person_count: number
}

export interface ClusterEvent {
  id: number
  title: string
  title_ko?: string
  title_ja?: string
  year?: number
  importance?: number
  category?: string
  location_name?: string
  location_name_ko?: string
  location_name_ja?: string
  lat?: number
  lng?: number
}

export interface SmartMarkersResponse {
  heroes: HeroMarker[]
  zoom: string
  total_events: number
}

// Content Report
export interface ContentReport {
  entity_type: string
  entity_id: number
  field_name?: string
  report_type: 'incorrect' | 'suspicious' | 'low_quality' | 'inappropriate' | 'other'
  reason: string
  suggested_correction?: string
}

// Source Detail (for SourceBrowser)
export interface SourceDetail {
  id: number
  title: string
  type: string
  author?: string
  url?: string
  mention_count?: number
  event_count?: number
  person_count?: number
}

// Source Mention (text_mentions)
export interface SourceMention {
  id: number
  entity_type: string
  entity_id: number
  entity_name: string
  context?: string
  position?: number
}

// Source Person (persons mentioned in a source)
export interface SourcePerson {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  wikidata_id?: string
  role?: string
  mention_count: number
}

// === Trismegistus Portal Types ===

export interface PortalLayer {
  type: 'home' | 'collection' | 'detail'
  slug?: string
  scrollY?: number
}

export interface PortalItemSummary {
  id: number
  slug: string
  item_type: string
  title: string
  title_ko?: string
  title_ja?: string
  subtitle?: string
  subtitle_ko?: string
  subtitle_ja?: string
  chapter?: string
  era?: string
  year?: number
  location?: string
  is_featured: boolean
  thumbnail_url?: string
  sort_order: number
}

export interface PortalItemDetail extends PortalItemSummary {
  description: string
  description_ko?: string
  description_ja?: string
  historical_basis?: string
  historical_basis_ko?: string
  historical_basis_ja?: string
  sections: Array<{
    title: string
    title_ko?: string
    title_ja?: string
    content: string
    content_ko?: string
    content_ja?: string
  }>
  related_servants: Array<{ name: string; class?: string; rarity?: number; slug?: string }>
  related_event_ids: number[]
  sources: string[]
}

export interface CollectionSummary {
  id: number
  slug: string
  collection_type: string
  title: string
  title_ko?: string
  title_ja?: string
  description?: string
  description_ko?: string
  description_ja?: string
  icon?: string
  cover_image_url?: string
  sort_order: number
  is_featured: boolean
  tags: string[]
  year_start?: number
  year_end?: number
  region?: string
  entry_count: number
}

export interface CollectionDetail extends CollectionSummary {
  entries: CollectionEntrySummary[]
}

export interface CollectionEntrySummary {
  id: number
  entry_type: string
  sort_order: number
  is_highlighted: boolean
  note?: string
  note_ko?: string
  portal_item?: PortalItemSummary
  shift_summary?: PortalShiftSummary
  person_summary?: PortalPersonSummary
  event_summary?: PortalEventSummary
  shift_id?: number
  person_id?: number
  event_id?: number
  period_id?: number
}

export interface PortalShiftSummary {
  id: number
  title: string
  title_ko?: string
  chain_type?: string
  year_start?: number
  year_end?: number
  segment_count?: number
}

export interface PortalPersonSummary {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
}

export interface PortalEventSummary {
  id: number
  title: string
  title_ko?: string
  date_start?: number
}

export interface RecommendationItem {
  type: 'shift' | 'portal_item' | 'collection'
  id?: number
  slug?: string
  title: string
  title_ko?: string
  subtitle?: string
  item_type?: string
  chain_type?: string
  icon?: string
  segment_count?: number
}

export interface PortalFeaturedResponse {
  items: PortalItemSummary[]
  collections: CollectionSummary[]
  recommendations: RecommendationItem[]
}

// Timeline / Period Types
export interface PeriodSummary {
  period_start: number
  period_end: number
  era_id?: string
  headline?: string
  headline_ko?: string
  event_count: number
  person_count: number
  region_count: number
  has_narrative: boolean
  date_display?: string
}

export interface PeriodEvent {
  id: number
  title: string
  title_ko?: string
  date_start: number
  date_end?: number
  date_display?: string
  importance_score?: number
  description?: string
  wikipedia_url?: string
  location_name?: string
  latitude?: number
  longitude?: number
  narrative?: string
  significance?: string
  is_aggregate?: boolean
  child_count?: number
}

export interface PeriodPerson {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  date_display?: string
  role?: string
  domain?: string
  score?: number
  wikipedia_url?: string
  image_url?: string
  narrative?: string
  significance?: string
}

export interface RegionNarrative {
  region: string
  region_name: string
  headline?: string
  narrative?: string
  keywords?: string[]
  quote?: string
  quote_source?: string
  event_count: number
  person_count: number
  top_events?: { title: string; date: string; score: number }[]
  top_persons?: { name: string; domain?: string; score: number }[]
  narrative_id?: number
}

export interface PeriodDetail {
  period_start: number
  period_end: number
  era_id?: string
  // Global overview
  headline?: string
  headline_ko?: string
  narrative?: string
  narrative_ko?: string
  defining_moment?: string
  curated_status?: string
  narrative_id?: number
  // Regional breakdowns
  regions: RegionNarrative[]
  // Flat event/person lists
  events: PeriodEvent[]
  persons: PeriodPerson[]
}
