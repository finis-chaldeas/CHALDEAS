/**
 * HistoryEditor - Create/edit modal for history essays
 *
 * - Entity autocomplete: type [ to trigger search
 * - Location and featured entity chips
 * - 4-paragraph soft limit warning
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { historiesApi, portalApi } from '../../api/client'
import type { History } from '../../types'
import './history.css'

interface HistoryEditorProps {
  historyId: number | null
  onClose: () => void
  onSaved: (id: number) => void
}

interface EntityChip {
  entity_type: string
  entity_id: number
  entity_name: string
}

interface SearchResult {
  id: number | string
  type: 'person' | 'event' | 'location' | 'shift' | 'item' | 'collection'
  name: string
  meta?: string
}

const CATEGORY_OPTIONS = ['essay', 'biography', 'causal_chain', 'era_overview', 'comparison']

function countParagraphs(text: string): number {
  return text.split(/\n\s*\n/).filter(p => p.trim().length > 0).length
}

export function HistoryEditor({ historyId, onClose, onSaved }: HistoryEditorProps) {
  const queryClient = useQueryClient()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Form state
  const [title, setTitle] = useState('')
  const [titleKo, setTitleKo] = useState('')
  const [summary, setSummary] = useState('')
  const [eraStart, setEraStart] = useState('')
  const [eraEnd, setEraEnd] = useState('')
  const [body, setBody] = useState('')
  const [bodyKo, setBodyKo] = useState('')
  const [category, setCategory] = useState('essay')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [authorName, setAuthorName] = useState('')
  const [importance, setImportance] = useState(3)
  const [featuredEntities, setFeaturedEntities] = useState<EntityChip[]>([])
  const [locations, setLocations] = useState<EntityChip[]>([])

  // Autocomplete state
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [autocompleteQuery, setAutocompleteQuery] = useState('')
  const [autocompleteResults, setAutocompleteResults] = useState<SearchResult[]>([])
  const [bracketStart, setBracketStart] = useState(-1)

  // Entity search for chips
  const [chipSearchQuery, setChipSearchQuery] = useState('')
  const [chipSearchTarget, setChipSearchTarget] = useState<'featured' | 'location' | null>(null)
  const [chipSearchResults, setChipSearchResults] = useState<SearchResult[]>([])

  const [saving, setSaving] = useState(false)

  // Load existing history for editing
  const { data: existing } = useQuery({
    queryKey: ['history-edit', historyId],
    queryFn: () => historiesApi.get(historyId!),
    select: (res) => res.data as History,
    enabled: historyId != null,
  })

  useEffect(() => {
    if (existing) {
      setTitle(existing.title)
      setTitleKo(existing.title_ko || '')
      setSummary(existing.summary || '')
      setEraStart(existing.era_start != null ? String(existing.era_start) : '')
      setEraEnd(existing.era_end != null ? String(existing.era_end) : '')
      setBody(existing.body)
      setBodyKo(existing.body_ko || '')
      setCategory(existing.category)
      setTags(existing.tags || [])
      setAuthorName(existing.author_name || '')
      setImportance(existing.importance)
      setFeaturedEntities(
        existing.entities
          .filter(e => e.role === 'featured')
          .map(e => ({ entity_type: e.entity_type, entity_id: e.entity_id, entity_name: e.entity_name || '' }))
      )
      setLocations(
        existing.entities
          .filter(e => e.role === 'location')
          .map(e => ({ entity_type: e.entity_type, entity_id: e.entity_id, entity_name: e.entity_name || '' }))
      )
    }
  }, [existing])

  // Debounced search for autocomplete via /portal/resolve (6 entity types)
  useEffect(() => {
    if (!autocompleteQuery || autocompleteQuery.length < 2) {
      setAutocompleteResults([])
      return
    }
    const timeout = setTimeout(async () => {
      try {
        const res = await portalApi.resolve(autocompleteQuery, { limit: 10 })
        const results: SearchResult[] = (res.data?.results || []).map(
          (r: { type: string; id: number | string; name: string; meta?: string }) => ({
            id: r.id,
            type: r.type as SearchResult['type'],
            name: r.name,
            meta: r.meta,
          })
        )
        setAutocompleteResults(results)
      } catch {
        setAutocompleteResults([])
      }
    }, 300)
    return () => clearTimeout(timeout)
  }, [autocompleteQuery])

  // Debounced search for chip adding via /portal/resolve
  useEffect(() => {
    if (!chipSearchQuery || chipSearchQuery.length < 2) {
      setChipSearchResults([])
      return
    }
    const timeout = setTimeout(async () => {
      try {
        const typeFilter = chipSearchTarget === 'location' ? 'location' : undefined
        const res = await portalApi.resolve(chipSearchQuery, {
          type_filter: typeFilter,
          limit: chipSearchTarget === 'location' ? 5 : 8,
        })
        const results: SearchResult[] = (res.data?.results || []).map(
          (r: { type: string; id: number | string; name: string; meta?: string }) => ({
            id: r.id,
            type: r.type as SearchResult['type'],
            name: r.name,
            meta: r.meta,
          })
        )
        setChipSearchResults(results)
      } catch {
        setChipSearchResults([])
      }
    }, 300)
    return () => clearTimeout(timeout)
  }, [chipSearchQuery, chipSearchTarget])

  // Handle textarea input for [ bracket detection
  const handleBodyChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    setBody(newValue)

    const textarea = textareaRef.current
    if (!textarea) return

    const cursorPos = textarea.selectionStart
    const textBefore = newValue.substring(0, cursorPos)

    // Find last unmatched [
    const lastBracket = textBefore.lastIndexOf('[')
    const lastCloseBracket = textBefore.lastIndexOf(']')

    if (lastBracket > lastCloseBracket && lastBracket >= 0) {
      const query = textBefore.substring(lastBracket + 1)
      if (query.length >= 1 && !query.includes('\n')) {
        setBracketStart(lastBracket)
        setAutocompleteQuery(query)
        setShowAutocomplete(true)
        return
      }
    }

    setShowAutocomplete(false)
    setAutocompleteQuery('')
  }, [])

  // Select autocomplete result
  const handleAutocompleteSelect = (result: SearchResult) => {
    if (bracketStart < 0) return

    const before = body.substring(0, bracketStart)
    const after = body.substring(textareaRef.current?.selectionStart || bracketStart)
    const tag = `[${result.name}](entity:${result.type}:${result.id})`
    const newBody = before + tag + after
    setBody(newBody)
    setShowAutocomplete(false)
    setAutocompleteQuery('')
    setBracketStart(-1)

    // Refocus textarea
    setTimeout(() => {
      if (textareaRef.current) {
        const pos = before.length + tag.length
        textareaRef.current.focus()
        textareaRef.current.selectionStart = pos
        textareaRef.current.selectionEnd = pos
      }
    }, 0)
  }

  // Add tag
  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()])
      setTagInput('')
    }
  }

  // Add chip entity (chips only support numeric IDs: person/event/location)
  const handleAddChip = (result: SearchResult) => {
    const chip: EntityChip = {
      entity_type: result.type,
      entity_id: typeof result.id === 'number' ? result.id : parseInt(String(result.id), 10),
      entity_name: result.name,
    }

    if (chipSearchTarget === 'location') {
      if (!locations.find(l => l.entity_id === result.id)) {
        setLocations([...locations, { ...chip, entity_type: 'location' }])
      }
    } else {
      if (!featuredEntities.find(e => e.entity_id === result.id && e.entity_type === result.type)) {
        setFeaturedEntities([...featuredEntities, chip])
      }
    }
    setChipSearchQuery('')
    setChipSearchResults([])
    setChipSearchTarget(null)
  }

  // Save
  const handleSave = async () => {
    if (!title.trim() || !body.trim()) return
    setSaving(true)

    const payload: Record<string, unknown> = {
      title: title.trim(),
      title_ko: titleKo.trim() || null,
      summary: summary.trim() || null,
      era_start: eraStart ? parseInt(eraStart, 10) : null,
      era_end: eraEnd ? parseInt(eraEnd, 10) : null,
      body: body,
      body_ko: bodyKo || null,
      category,
      tags,
      author_type: 'user',
      author_name: authorName.trim() || null,
      importance,
      featured_entities: featuredEntities.map(e => ({
        entity_type: e.entity_type,
        entity_id: e.entity_id,
        entity_name: e.entity_name,
      })),
      locations: locations.map(l => ({
        entity_type: 'location',
        entity_id: l.entity_id,
        entity_name: l.entity_name,
      })),
    }

    try {
      let res
      if (historyId) {
        res = await historiesApi.update(historyId, payload)
      } else {
        res = await historiesApi.create(payload)
      }
      queryClient.invalidateQueries({ queryKey: ['navigator-histories'] })
      queryClient.invalidateQueries({ queryKey: ['history-detail'] })
      onSaved(res.data.id)
    } catch (err) {
      console.error('Failed to save history:', err)
    } finally {
      setSaving(false)
    }
  }

  const paragraphCount = countParagraphs(body)

  return (
    <div className="history-editor-overlay" onClick={(e) => {
      if (e.target === e.currentTarget) onClose()
    }}>
      <div className="history-editor-modal">
        {/* Header */}
        <div className="history-editor-header">
          <span className="history-editor-title-text">
            {historyId ? 'Edit History' : 'New History'}
          </span>
          <div className="history-editor-header-actions">
            <button
              className="history-editor-save"
              onClick={handleSave}
              disabled={saving || !title.trim() || !body.trim()}
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button className="history-editor-close" onClick={onClose}>{'\u2715'}</button>
          </div>
        </div>

        <div className="history-editor-form">
          {/* Title */}
          <div className="history-editor-field">
            <label>Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="History title"
              className="history-editor-input"
            />
          </div>

          <div className="history-editor-field">
            <label>Title (KO)</label>
            <input
              type="text"
              value={titleKo}
              onChange={(e) => setTitleKo(e.target.value)}
              placeholder="Korean title (optional)"
              className="history-editor-input"
            />
          </div>

          {/* Era + Category row */}
          <div className="history-editor-row">
            <div className="history-editor-field history-editor-field-sm">
              <label>Era Start</label>
              <input
                type="number"
                value={eraStart}
                onChange={(e) => setEraStart(e.target.value)}
                placeholder="-490"
                className="history-editor-input"
              />
            </div>
            <div className="history-editor-field history-editor-field-sm">
              <label>Era End</label>
              <input
                type="number"
                value={eraEnd}
                onChange={(e) => setEraEnd(e.target.value)}
                placeholder="-27"
                className="history-editor-input"
              />
            </div>
            <div className="history-editor-field history-editor-field-sm">
              <label>Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="history-editor-input"
              >
                {CATEGORY_OPTIONS.map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Summary */}
          <div className="history-editor-field">
            <label>Summary</label>
            <input
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="1-2 line summary"
              className="history-editor-input"
              maxLength={500}
            />
          </div>

          {/* Locations */}
          <div className="history-editor-field">
            <label>{'\uD83D\uDCCD'} Locations</label>
            <div className="history-editor-chips">
              {locations.map((loc, i) => (
                <span key={i} className="entity-chip entity-chip-location">
                  {loc.entity_name}
                  <button onClick={() => setLocations(locations.filter((_, j) => j !== i))}>{'\u2715'}</button>
                </span>
              ))}
              <button
                className="history-editor-add-chip"
                onClick={() => { setChipSearchTarget('location'); setChipSearchQuery(''); }}
              >
                + Add
              </button>
            </div>
          </div>

          {/* Featured entities */}
          <div className="history-editor-field">
            <label>{'\u263E'} Featured Entities</label>
            <div className="history-editor-chips">
              {featuredEntities.map((ent, i) => (
                <span key={i} className={`entity-chip entity-chip-${ent.entity_type}`}>
                  {ent.entity_name}
                  <button onClick={() => setFeaturedEntities(featuredEntities.filter((_, j) => j !== i))}>{'\u2715'}</button>
                </span>
              ))}
              <button
                className="history-editor-add-chip"
                onClick={() => { setChipSearchTarget('featured'); setChipSearchQuery(''); }}
              >
                + Add
              </button>
            </div>
          </div>

          {/* Chip search dropdown */}
          {chipSearchTarget && (
            <div className="history-editor-chip-search">
              <input
                type="text"
                value={chipSearchQuery}
                onChange={(e) => setChipSearchQuery(e.target.value)}
                placeholder={`Search ${chipSearchTarget === 'location' ? 'locations' : 'entities'}...`}
                className="history-editor-input"
                autoFocus
              />
              {chipSearchResults.length > 0 && (
                <div className="history-editor-chip-results">
                  {chipSearchResults.map(r => (
                    <button key={`${r.type}-${r.id}`} onClick={() => handleAddChip(r)}>
                      <span className="chip-result-type">
                        {r.type === 'person' ? '\u263E'
                          : r.type === 'event' ? '\u25CE'
                          : r.type === 'location' ? '\uD83D\uDCCD'
                          : r.type === 'shift' ? '\u25B6'
                          : r.type === 'item' ? '\uD83D\uDCD6'
                          : '\uD83C\uDFDB'}
                      </span>
                      {r.name}
                    </button>
                  ))}
                </div>
              )}
              <button className="history-editor-chip-cancel" onClick={() => setChipSearchTarget(null)}>Cancel</button>
            </div>
          )}

          {/* Body */}
          <div className="history-editor-field">
            <label>Body (Markdown)</label>
            <div className="history-editor-body-hint">
              Type <code>[</code> to insert entity tags. Use <code>[Name](entity:type:id)</code> format.
            </div>
            <div className="history-editor-textarea-wrapper">
              <textarea
                ref={textareaRef}
                value={body}
                onChange={handleBodyChange}
                placeholder="Write your history essay here..."
                className="history-editor-textarea"
                rows={12}
              />
              {/* Autocomplete dropdown */}
              {showAutocomplete && autocompleteResults.length > 0 && (
                <div className="history-editor-autocomplete">
                  {autocompleteResults.map(r => (
                    <button
                      key={`${r.type}-${r.id}`}
                      className="autocomplete-item"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        handleAutocompleteSelect(r)
                      }}
                    >
                      <span className="autocomplete-type">
                        {r.type === 'person' ? '\u263E'
                          : r.type === 'event' ? '\u25CE'
                          : r.type === 'location' ? '\uD83D\uDCCD'
                          : r.type === 'shift' ? '\u25B6'
                          : r.type === 'item' ? '\uD83D\uDCD6'
                          : '\uD83C\uDFDB'}
                      </span>
                      <span className="autocomplete-name">{r.name}</span>
                      {r.meta && <span className="autocomplete-meta">{r.meta}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="history-editor-body-meta">
              <span>{paragraphCount} paragraph{paragraphCount !== 1 ? 's' : ''}</span>
              {paragraphCount > 4 && (
                <span className="history-editor-warning">Consider splitting into multiple histories</span>
              )}
            </div>
          </div>

          {/* Body KO */}
          <div className="history-editor-field">
            <label>Body (Korean, optional)</label>
            <textarea
              value={bodyKo}
              onChange={(e) => setBodyKo(e.target.value)}
              placeholder="Korean body (optional)"
              className="history-editor-textarea"
              rows={6}
            />
          </div>

          {/* Tags */}
          <div className="history-editor-field">
            <label>Tags</label>
            <div className="history-editor-tags">
              {tags.map((tag, i) => (
                <span key={i} className="history-tag">
                  {tag}
                  <button onClick={() => setTags(tags.filter((_, j) => j !== i))}>{'\u2715'}</button>
                </span>
              ))}
              <div className="history-editor-tag-input">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') { e.preventDefault(); handleAddTag() }
                  }}
                  placeholder="Add tag..."
                />
                <button onClick={handleAddTag}>+</button>
              </div>
            </div>
          </div>

          {/* Author + Importance */}
          <div className="history-editor-row">
            <div className="history-editor-field">
              <label>Author Name</label>
              <input
                type="text"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                placeholder="Your name (optional)"
                className="history-editor-input"
              />
            </div>
            <div className="history-editor-field history-editor-field-sm">
              <label>Importance (1-5)</label>
              <input
                type="number"
                value={importance}
                onChange={(e) => setImportance(Math.max(1, Math.min(5, parseInt(e.target.value) || 3)))}
                min={1}
                max={5}
                className="history-editor-input"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HistoryEditor
