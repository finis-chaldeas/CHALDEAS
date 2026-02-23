/**
 * HistoryTab - List of authored historical essays
 *
 * - Filterable by category and era
 * - Click to open HistoryViewer
 * - Button to create new history
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { historiesApi } from '../../api/client'
import type { HistoryListItem } from '../../types'

interface HistoryTabProps {
  onHistoryClick: (historyId: number) => void
  onCreateHistory: () => void
}

const CATEGORY_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'essay', label: 'Essay' },
  { value: 'biography', label: 'Biography' },
  { value: 'causal_chain', label: 'Causal Chain' },
  { value: 'era_overview', label: 'Era Overview' },
  { value: 'comparison', label: 'Comparison' },
]

function formatEra(start?: number, end?: number): string {
  if (start == null && end == null) return ''
  const fmt = (y: number) => y < 0 ? `${Math.abs(y)} BCE` : `${y} CE`
  if (start != null && end != null) return `${fmt(start)} ~ ${fmt(end)}`
  if (start != null) return `from ${fmt(start)}`
  return `until ${fmt(end!)}`
}

export function HistoryTab({ onHistoryClick, onCreateHistory }: HistoryTabProps) {
  const { t } = useTranslation()
  const [categoryFilter, setCategoryFilter] = useState('')

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = { limit: 100 }
    if (categoryFilter) params.category = categoryFilter
    return params
  }, [categoryFilter])

  const { data, isLoading } = useQuery({
    queryKey: ['navigator-histories', queryParams],
    queryFn: () => historiesApi.list(queryParams),
    select: (res) => res.data,
  })

  const histories: HistoryListItem[] = data?.items || []

  return (
    <div className="navigator-tab-content">
      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-controls-row">
          <button
            className="nav-create-btn"
            onClick={onCreateHistory}
          >
            + {t('navigator.newHistory', 'New History')}
          </button>
          <select
            className="nav-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            {CATEGORY_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="nav-result-count">
          {histories.length} {t('navigator.histories', 'histories')}
        </div>
      </div>

      {/* List */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : histories.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noHistories', 'No histories yet')}</div>
        ) : (
          histories.map((history) => {
            const era = formatEra(history.era_start, history.era_end)

            return (
              <button
                key={history.id}
                className="nav-history-card"
                onClick={() => onHistoryClick(history.id)}
              >
                <div className="nav-history-icon">{'\uD83D\uDCDC'}</div>
                <div className="nav-history-body">
                  <div className="nav-history-title">{history.title_ko || history.title}</div>
                  <div className="nav-history-meta">
                    {era && <span className="nav-history-era">{era}</span>}
                    <span className="nav-history-entities">{history.entity_count} entities</span>
                  </div>
                  <div className="nav-history-meta2">
                    <span className="nav-history-author">by {history.author_type}</span>
                    <span className="nav-history-category">{history.category}</span>
                  </div>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
