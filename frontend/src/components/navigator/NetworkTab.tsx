/**
 * NetworkTab - Person relationship network
 *
 * Shows persons in the current viewport/era with their inter-relationships
 * from the links table (family: child, father, mother, spouse, sibling).
 * Displayed as an indented tree using CSS.
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../api/client'
import type { ViewportBounds, ZoomLevel } from '../../store/globeStore'

interface NetworkTabProps {
  currentYear: number
  viewportBounds: ViewportBounds | null
  zoomLevel: ZoomLevel
  onPersonClick: (personId: number) => void
  onOpenStory: (personId: number) => void
}

interface NetworkPerson {
  id: number
  name: string
  name_ko?: string
  birth_year?: number
  death_year?: number
  role?: string
  connection_count?: number
}

interface Relation {
  from_id: number
  to_id: number
  category: string
}

// Build relationship trees from flat relations
interface PersonNode {
  person: NetworkPerson
  children: { relation: string; node: PersonNode }[]
}

const TIME_RANGE = 200

const RELATION_LABELS: Record<string, string> = {
  child: 'parent of',
  father: 'child of',
  mother: 'child of',
  spouse: 'spouse',
  sibling: 'sibling',
  relative: 'relative',
  partner: 'partner',
}

const RELATION_COLORS: Record<string, string> = {
  child: '#fbbf24',
  father: '#60a5fa',
  mother: '#f472b6',
  spouse: '#f87171',
  sibling: '#34d399',
  relative: '#a78bfa',
  partner: '#fb923c',
}

function formatYear(year: number | null | undefined): string {
  if (year === null || year === undefined) return '?'
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year}`
}

function buildTrees(persons: NetworkPerson[], relations: Relation[]): PersonNode[] {
  const personMap = new Map<number, NetworkPerson>()
  persons.forEach(p => personMap.set(p.id, p))

  // Track which persons appear as "children" in a tree
  const childIds = new Set<number>()
  const adjacency = new Map<number, { targetId: number; relation: string }[]>()

  for (const rel of relations) {
    // "child" means from_id is child of to_id, so to_id is parent
    // We want to show: parent -> "parent of" -> child
    if (rel.category === 'child') {
      // from_id is child, to_id is parent
      if (!adjacency.has(rel.to_id)) adjacency.set(rel.to_id, [])
      adjacency.get(rel.to_id)!.push({ targetId: rel.from_id, relation: 'child' })
      childIds.add(rel.from_id)
    } else if (rel.category === 'father' || rel.category === 'mother') {
      // from_id's father/mother is to_id → to_id is parent of from_id
      if (!adjacency.has(rel.to_id)) adjacency.set(rel.to_id, [])
      adjacency.get(rel.to_id)!.push({ targetId: rel.from_id, relation: rel.category })
      childIds.add(rel.from_id)
    } else if (rel.category === 'spouse') {
      // Show spouse as sub-item of the one with higher connection count
      const fromP = personMap.get(rel.from_id)
      const toP = personMap.get(rel.to_id)
      if (fromP && toP) {
        const fromConn = fromP.connection_count || 0
        const toConn = toP.connection_count || 0
        if (fromConn >= toConn) {
          if (!adjacency.has(rel.from_id)) adjacency.set(rel.from_id, [])
          adjacency.get(rel.from_id)!.push({ targetId: rel.to_id, relation: 'spouse' })
          childIds.add(rel.to_id)
        } else {
          if (!adjacency.has(rel.to_id)) adjacency.set(rel.to_id, [])
          adjacency.get(rel.to_id)!.push({ targetId: rel.from_id, relation: 'spouse' })
          childIds.add(rel.from_id)
        }
      }
    } else if (rel.category === 'sibling') {
      // Show sibling under the one with higher connection count
      const fromP = personMap.get(rel.from_id)
      const toP = personMap.get(rel.to_id)
      if (fromP && toP) {
        const fromConn = fromP.connection_count || 0
        const toConn = toP.connection_count || 0
        if (fromConn >= toConn) {
          if (!adjacency.has(rel.from_id)) adjacency.set(rel.from_id, [])
          adjacency.get(rel.from_id)!.push({ targetId: rel.to_id, relation: 'sibling' })
          childIds.add(rel.to_id)
        } else {
          if (!adjacency.has(rel.to_id)) adjacency.set(rel.to_id, [])
          adjacency.get(rel.to_id)!.push({ targetId: rel.from_id, relation: 'sibling' })
          childIds.add(rel.from_id)
        }
      }
    }
  }

  // Build trees from root persons (not appearing as children)
  const visited = new Set<number>()

  function buildNode(personId: number, depth: number): PersonNode | null {
    if (visited.has(personId) || depth > 4) return null
    const person = personMap.get(personId)
    if (!person) return null

    visited.add(personId)
    const children: PersonNode['children'] = []
    const adj = adjacency.get(personId) || []

    for (const { targetId, relation } of adj) {
      const childNode = buildNode(targetId, depth + 1)
      if (childNode) {
        children.push({ relation, node: childNode })
      }
    }

    return { person, children }
  }

  const trees: PersonNode[] = []

  // First: build trees from root persons
  for (const p of persons) {
    if (!childIds.has(p.id) && !visited.has(p.id)) {
      const node = buildNode(p.id, 0)
      if (node) trees.push(node)
    }
  }

  // Then: add isolated persons (no relations in viewport)
  for (const p of persons) {
    if (!visited.has(p.id)) {
      trees.push({ person: p, children: [] })
    }
  }

  return trees
}

function PersonTreeNode({
  node,
  relation,
  depth,
  onPersonClick,
  onOpenStory,
}: {
  node: PersonNode
  relation?: string
  depth: number
  onPersonClick: (id: number) => void
  onOpenStory: (id: number) => void
}) {
  const p = node.person
  const lifespan = (p.birth_year != null || p.death_year != null)
    ? `${formatYear(p.birth_year)} \u2013 ${formatYear(p.death_year)}`
    : ''

  return (
    <div className="network-tree-node" style={{ paddingLeft: `${depth * 16}px` }}>
      <div className="network-person-row">
        {relation && (
          <span
            className="network-relation-label"
            style={{ color: RELATION_COLORS[relation] || '#888' }}
          >
            {RELATION_LABELS[relation] || relation} &rarr;
          </span>
        )}
        <button
          className="network-person-name"
          onClick={() => onPersonClick(p.id)}
        >
          {p.name}
        </button>
        {lifespan && <span className="network-lifespan">{lifespan}</span>}
        <button
          className="network-story-btn"
          onClick={() => onOpenStory(p.id)}
          title="Open Story"
        >
          &#9654;
        </button>
      </div>
      {node.children.map(({ relation: rel, node: child }, idx) => (
        <PersonTreeNode
          key={`${child.person.id}-${idx}`}
          node={child}
          relation={rel}
          depth={depth + 1}
          onPersonClick={onPersonClick}
          onOpenStory={onOpenStory}
        />
      ))}
    </div>
  )
}

export function NetworkTab({
  currentYear,
  viewportBounds,
  zoomLevel,
  onPersonClick,
  onOpenStory,
}: NetworkTabProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedYear = useDebounce(currentYear, 150)
  const debouncedBounds = useDebounce(viewportBounds, 300)

  const queryParams = useMemo(() => {
    const params: Record<string, unknown> = {
      year_start: debouncedYear - TIME_RANGE,
      year_end: debouncedYear + TIME_RANGE,
      limit: 30,
    }

    if (zoomLevel !== 'cosmic' && debouncedBounds) {
      params.lat_min = debouncedBounds.south
      params.lat_max = debouncedBounds.north
      params.lng_min = debouncedBounds.west
      params.lng_max = debouncedBounds.east
    }

    return params
  }, [debouncedYear, zoomLevel, debouncedBounds])

  const { data, isLoading } = useQuery({
    queryKey: ['navigator-network', queryParams],
    queryFn: () => api.get('/persons/network', { params: queryParams }),
    select: (res) => res.data,
  })

  const persons: NetworkPerson[] = data?.persons || []
  const relations: Relation[] = data?.relations || []

  const trees = useMemo(() => {
    if (persons.length === 0) return []
    return buildTrees(persons, relations)
  }, [persons, relations])

  // Filter by search
  const filteredTrees = useMemo(() => {
    if (!searchQuery) return trees
    const q = searchQuery.toLowerCase()

    function matchesSearch(node: PersonNode): boolean {
      if (node.person.name.toLowerCase().includes(q)) return true
      return node.children.some(c => matchesSearch(c.node))
    }

    return trees.filter(matchesSearch)
  }, [trees, searchQuery])

  const relationCount = relations.length

  return (
    <div className="navigator-tab-content">
      {/* Controls */}
      <div className="nav-controls">
        <div className="nav-controls-row">
          <input
            type="text"
            placeholder={t('navigator.searchNetwork', 'Search persons...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="nav-search-input"
          />
        </div>
        <div className="nav-result-count">
          {persons.length} {t('navigator.persons', 'persons')}
          {relationCount > 0 && <span className="network-relation-count">{relationCount} links</span>}
          {zoomLevel !== 'cosmic' && <span className="nav-viewport-tag">viewport</span>}
        </div>
      </div>

      {/* Tree */}
      <div className="nav-list">
        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : filteredTrees.length === 0 ? (
          <div className="navigator-empty">{t('navigator.noPersons', 'No persons found')}</div>
        ) : (
          filteredTrees.map((tree) => (
            <PersonTreeNode
              key={tree.person.id}
              node={tree}
              depth={0}
              onPersonClick={onPersonClick}
              onOpenStory={onOpenStory}
            />
          ))
        )}
      </div>
    </div>
  )
}
