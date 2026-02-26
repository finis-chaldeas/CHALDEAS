import { useState, useEffect } from 'react'
import { shiftsApi } from '../../api/client'
import { useGlobeStore } from '../../store/globeStore'
import type { HistoryShift } from '../../types'
import './ShiftBrowser.css'

function formatYear(year: number | undefined | null): string {
  if (year == null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function getEraLabel(year: number): string {
  if (year < -3000) return 'Prehistoric'
  if (year < -500) return 'Ancient'
  if (year < 500) return 'Classical'
  if (year < 1500) return 'Medieval'
  if (year < 1800) return 'Early Modern'
  if (year < 1945) return 'Modern'
  return 'Contemporary'
}

interface ShiftBrowserProps {
  isOpen: boolean
  onClose: () => void
}

export default function ShiftBrowser({ isOpen, onClose }: ShiftBrowserProps) {
  const openShift = useGlobeStore((s) => s.openShift)
  const [shifts, setShifts] = useState<HistoryShift[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filterEra, setFilterEra] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const LIMIT = 50

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setOffset(0)
    shiftsApi.list({ limit: LIMIT, offset: 0 })
      .then((res) => {
        setShifts(res.data?.items || [])
        setTotal(res.data?.total || 0)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [isOpen])

  const loadMore = () => {
    const newOffset = offset + LIMIT
    setLoading(true)
    shiftsApi.list({ limit: LIMIT, offset: newOffset })
      .then((res) => {
        setShifts((prev) => [...prev, ...(res.data?.items || [])])
        setOffset(newOffset)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  const handleOpen = async (shift: HistoryShift) => {
    try {
      const res = await shiftsApi.get(shift.id)
      if (res.data?.pages?.length > 0) {
        openShift(res.data)
        onClose()
      }
    } catch (err) {
      console.error('Failed to load shift:', err)
    }
  }

  if (!isOpen) return null

  // Filter by era and search
  const filtered = shifts.filter((s) => {
    if (filterEra !== 'all' && getEraLabel(s.year_start) !== filterEra) return false
    if (search) {
      const q = search.toLowerCase()
      return (s.title?.toLowerCase().includes(q) || s.title_ko?.toLowerCase().includes(q))
    }
    return true
  })

  // Group by era
  const grouped = new Map<string, HistoryShift[]>()
  for (const s of filtered) {
    const era = getEraLabel(s.year_start)
    if (!grouped.has(era)) grouped.set(era, [])
    grouped.get(era)!.push(s)
  }

  const eraOrder = ['Prehistoric', 'Ancient', 'Classical', 'Medieval', 'Early Modern', 'Modern', 'Contemporary']

  return (
    <div className="sb-overlay" onClick={onClose}>
      <div className="sb-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="sb-header">
          <h2>History Shifts</h2>
          <span className="sb-count">{total} shifts</span>
          <button className="sb-close" onClick={onClose}>&times;</button>
        </div>

        {/* Filters */}
        <div className="sb-filters">
          <input
            className="sb-search"
            type="text"
            placeholder="Search shifts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
          <div className="sb-era-tabs">
            <button
              className={`sb-era-tab ${filterEra === 'all' ? 'active' : ''}`}
              onClick={() => setFilterEra('all')}
            >
              All
            </button>
            {eraOrder.map((era) => (
              <button
                key={era}
                className={`sb-era-tab ${filterEra === era ? 'active' : ''}`}
                onClick={() => setFilterEra(era)}
              >
                {era}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="sb-list">
          {loading && shifts.length === 0 && (
            <div className="sb-loading">Loading shifts...</div>
          )}

          {filterEra === 'all' && !search ? (
            // Grouped by era
            eraOrder.map((era) => {
              const items = grouped.get(era)
              if (!items || items.length === 0) return null
              return (
                <div key={era} className="sb-era-group">
                  <div className="sb-era-label">{era} ({items.length})</div>
                  {items.map((s) => (
                    <ShiftCard key={s.id} shift={s} onOpen={handleOpen} />
                  ))}
                </div>
              )
            })
          ) : (
            // Flat filtered list
            filtered.map((s) => (
              <ShiftCard key={s.id} shift={s} onOpen={handleOpen} />
            ))
          )}

          {filtered.length === 0 && !loading && (
            <div className="sb-empty">No shifts found</div>
          )}

          {/* Load more */}
          {shifts.length < total && (
            <button className="sb-load-more" onClick={loadMore} disabled={loading}>
              {loading ? 'Loading...' : `Load more (${shifts.length}/${total})`}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ShiftCard({ shift, onOpen }: { shift: HistoryShift; onOpen: (s: HistoryShift) => void }) {
  return (
    <button className="sb-card" onClick={() => onOpen(shift)}>
      <div className="sb-card-main">
        <span className="sb-card-title">{shift.title_ko || shift.title}</span>
        {shift.title_ko && <span className="sb-card-subtitle">{shift.title}</span>}
      </div>
      <div className="sb-card-meta">
        <span className="sb-card-year">
          {formatYear(shift.year_start)}
          {shift.year_end ? ` ~ ${formatYear(shift.year_end)}` : ''}
        </span>
        <span className="sb-card-pages">{shift.page_count}p</span>
      </div>
    </button>
  )
}
