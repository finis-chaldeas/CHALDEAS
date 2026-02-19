/**
 * EventHierarchyPanel - Browse events in hierarchical tree view
 *
 * Shows aggregate events (wars, movements, dynasties) with their child events.
 * Supports expanding/collapsing nodes and selecting events.
 */
import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import './EventHierarchyPanel.css'

interface HierarchyNode {
  id: number
  title: string
  title_ko?: string
  date_start: number
  date_end?: number
  hierarchy_level: number
  is_aggregate: boolean
  aggregate_type?: string
  importance: number
  children: HierarchyNode[]
  child_count: number
}

interface HierarchyResponse {
  tree: HierarchyNode[]
  count: number
}

interface EventHierarchyPanelProps {
  isOpen: boolean
  onClose: () => void
  onSelectEvent: (eventId: number) => void
  language?: 'en' | 'ko'
}

const AGGREGATE_TYPE_ICONS: Record<string, string> = {
  war: '⚔️',
  movement: '🌊',
  dynasty: '👑',
  expedition: '🚢',
  revolution: '🔥',
  crisis: '⚠️',
  artistic_period: '🎨',
  philosophical_school: '💭',
  scientific_era: '🔬',
  religious: '✝️',
}

const HIERARCHY_LEVEL_COLORS: Record<number, string> = {
  0: '#ff6b6b', // Era - red
  1: '#ffa94d', // Mega - orange
  2: '#69db7c', // Aggregate - green
  3: '#74c0fc', // Major - blue
  4: '#b197fc', // Minor - purple
}

function formatYear(year: number): string {
  const absYear = Math.abs(year)
  return year < 0 ? `${absYear} BCE` : `${absYear} CE`
}

function formatDateRange(start: number, end?: number): string {
  if (!end || end === start) {
    return formatYear(start)
  }
  return `${formatYear(start)} - ${formatYear(end)}`
}

interface TreeNodeProps {
  node: HierarchyNode
  level: number
  expanded: Set<number>
  onToggle: (id: number) => void
  onSelect: (id: number) => void
  language: 'en' | 'ko'
}

function TreeNode({ node, level, expanded, onToggle, onSelect, language }: TreeNodeProps) {
  const isExpanded = expanded.has(node.id)
  const hasChildren = node.child_count > 0
  const icon = node.aggregate_type ? AGGREGATE_TYPE_ICONS[node.aggregate_type] : '📅'
  const title = language === 'ko' && node.title_ko ? node.title_ko : node.title

  return (
    <div className="tree-node" style={{ marginLeft: level * 16 }}>
      <div
        className={`tree-node-content ${node.is_aggregate ? 'aggregate' : ''}`}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren && (
          <button
            className="tree-expand-btn"
            onClick={(e) => {
              e.stopPropagation()
              onToggle(node.id)
            }}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        )}
        {!hasChildren && <span className="tree-expand-placeholder" />}

        <span className="tree-icon">{icon}</span>

        <span className="tree-title">{title}</span>

        <span
          className="tree-level-badge"
          style={{ backgroundColor: HIERARCHY_LEVEL_COLORS[node.hierarchy_level] || '#888' }}
        >
          L{node.hierarchy_level}
        </span>

        <span className="tree-date">{formatDateRange(node.date_start, node.date_end)}</span>

        {hasChildren && (
          <span className="tree-child-count">({node.child_count})</span>
        )}
      </div>

      {isExpanded && node.children && node.children.length > 0 && (
        <div className="tree-children">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
              language={language}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function EventHierarchyPanel({
  isOpen,
  onClose,
  onSelectEvent,
  language = 'en',
}: EventHierarchyPanelProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [filterType, setFilterType] = useState<string>('')

  const { data, isLoading, error } = useQuery<HierarchyResponse>({
    queryKey: ['event-hierarchy', filterType],
    queryFn: async () => {
      const params: Record<string, unknown> = { max_depth: 2 }
      const res = await api.get('/events/hierarchy', { params })
      return res.data
    },
    enabled: isOpen,
  })

  const handleToggle = useCallback((id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleExpandAll = useCallback(() => {
    if (data?.tree) {
      const allIds = new Set<number>()
      const collectIds = (nodes: HierarchyNode[]) => {
        for (const node of nodes) {
          if (node.child_count > 0) {
            allIds.add(node.id)
          }
          if (node.children) {
            collectIds(node.children)
          }
        }
      }
      collectIds(data.tree)
      setExpanded(allIds)
    }
  }, [data])

  const handleCollapseAll = useCallback(() => {
    setExpanded(new Set())
  }, [])

  if (!isOpen) return null

  // Filter tree by aggregate type
  let filteredTree = data?.tree || []
  if (filterType) {
    filteredTree = filteredTree.filter((node) => node.aggregate_type === filterType)
  }

  return (
    <div className="hierarchy-panel-overlay" onClick={onClose}>
      <div className="hierarchy-panel" onClick={(e) => e.stopPropagation()}>
        <header className="hierarchy-header">
          <div className="hierarchy-title">
            <span className="hierarchy-icon">🌲</span>
            <h2>Event Hierarchy</h2>
            <span className="hierarchy-subtitle">Browse by aggregate events</span>
          </div>
          <button className="hierarchy-close" onClick={onClose}>✕</button>
        </header>

        <div className="hierarchy-controls">
          <select
            className="hierarchy-filter"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="war">⚔️ Wars</option>
            <option value="dynasty">👑 Dynasties</option>
            <option value="movement">🌊 Movements</option>
            <option value="expedition">🚢 Expeditions</option>
            <option value="revolution">🔥 Revolutions</option>
            <option value="artistic_period">🎨 Art Periods</option>
            <option value="philosophical_school">💭 Philosophy</option>
            <option value="scientific_era">🔬 Science</option>
            <option value="religious">✝️ Religious</option>
          </select>

          <div className="hierarchy-expand-controls">
            <button onClick={handleExpandAll}>Expand All</button>
            <button onClick={handleCollapseAll}>Collapse All</button>
          </div>
        </div>

        <div className="hierarchy-legend">
          <span>Levels: </span>
          {Object.entries(HIERARCHY_LEVEL_COLORS).map(([level, color]) => (
            <span key={level} className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: color }} />
              L{level}
            </span>
          ))}
        </div>

        <div className="hierarchy-content">
          {isLoading && <div className="hierarchy-loading">Loading hierarchy...</div>}

          {error && (
            <div className="hierarchy-error">
              Failed to load hierarchy. Make sure the API server is running.
            </div>
          )}

          {!isLoading && !error && filteredTree.length === 0 && (
            <div className="hierarchy-empty">
              No aggregate events found. Run the classification pipeline first.
            </div>
          )}

          {!isLoading && !error && filteredTree.length > 0 && (
            <div className="hierarchy-tree">
              {filteredTree.map((node) => (
                <TreeNode
                  key={node.id}
                  node={node}
                  level={0}
                  expanded={expanded}
                  onToggle={handleToggle}
                  onSelect={onSelectEvent}
                  language={language}
                />
              ))}
            </div>
          )}
        </div>

        <footer className="hierarchy-footer">
          <span>
            {filteredTree.length} aggregate events
            {data?.count !== filteredTree.length && ` (${data?.count} total)`}
          </span>
        </footer>
      </div>
    </div>
  )
}

export default EventHierarchyPanel
