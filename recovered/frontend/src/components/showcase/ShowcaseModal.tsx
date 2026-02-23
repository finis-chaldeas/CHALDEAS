/**
 * ShowcaseModal - Trismegistus Archive Content Showcase
 * Displays curated content like Singularities, Lostbelts, Servant columns.
 * When content is null, shows ShowcaseMenu for browsing.
 */
import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ShowcaseMenu } from './ShowcaseMenu'
import { ServantTab } from '../navigator/ServantTab'
import { EraTab } from '../navigator/EraTab'
import { HistoryTab } from '../navigator/HistoryTab'
import { PersonTab } from '../navigator/PersonTab'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import type { Event } from '../../types'
import './showcase.css'

export interface ShowcaseContent {
  id: string
  type: 'singularity' | 'lostbelt' | 'servant' | 'article'
  title: string
  subtitle?: string
  chapter?: string
  era?: string
  year?: number
  location?: string
  image?: string
  description: string
  sections?: {
    title: string
    content: string
  }[]
  relatedEvents?: {
    id: number
    title: string
    year: number
  }[]
  relatedServants?: {
    name: string
    class: string
    rarity: number
  }[]
  historicalBasis?: string
  sources?: string[]
}

interface Props {
  isOpen: boolean
  content: ShowcaseContent | null
  onClose: () => void
  onEventClick?: (eventId: number) => void
  onPersonClick?: (personId: number) => void
  onFlyToLocation?: (lat: number, lng: number) => void
  onSetCurrentYear?: (year: number) => void
  onHistoryClick?: (historyId: number) => void
  onCreateHistory?: () => void
}

type ShowcaseView = 'menu' | 'content' | 'servants'
type ShowcaseTab = 'era' | 'fgo' | 'reading' | 'explore'

export function ShowcaseModal({ isOpen, content, onClose, onEventClick, onPersonClick, onFlyToLocation, onSetCurrentYear, onHistoryClick, onCreateHistory }: Props) {
  const { t } = useTranslation()
  const currentYear = useTimelineStore((s) => s.currentYear)
  const viewportBounds = useGlobeStore((s) => s.viewportBounds)
  const zoomLevel = useGlobeStore((s) => s.zoomLevel)
  const [internalContent, setInternalContent] = useState<ShowcaseContent | null>(null)
  const [view, setView] = useState<ShowcaseView>('menu')
  const [activeTab, setActiveTab] = useState<ShowcaseTab>('fgo')

  // Sync external content prop
  useEffect(() => {
    if (isOpen) {
      if (content) {
        setInternalContent(content)
        setView('content')
      } else {
        setInternalContent(null)
        setView('menu')
      }
    }
  }, [isOpen, content])

  // Close on Escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (view === 'content' || view === 'servants') {
        setView('menu')
        setInternalContent(null)
      } else {
        onClose()
      }
    }
  }, [onClose, view])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  const handleSelectContent = (selected: ShowcaseContent) => {
    setInternalContent(selected)
    setView('content')
  }

  const handleBack = () => {
    setInternalContent(null)
    setView('menu')
  }

  const handleClose = () => {
    setInternalContent(null)
    setView('menu')
    onClose()
  }

  // Handle EraTab event click (converts Event object to setCurrentYear call)
  const handleEraEventClick = (event: Event) => {
    if (event.date_start) {
      onSetCurrentYear?.(event.date_start)
    }
    if (onEventClick && event.id) {
      onEventClick(typeof event.id === 'number' ? event.id : parseInt(String(event.id), 10))
    }
    handleClose()
  }

  const TABS: { id: ShowcaseTab; label: string; icon: string }[] = [
    { id: 'era', label: t('showcase.tabs.era', 'Era'), icon: '\u26F0' },
    { id: 'fgo', label: t('showcase.tabs.fgo', 'FGO'), icon: '\u25CE' },
    { id: 'reading', label: t('showcase.tabs.reading', 'Reading'), icon: '\uD83D\uDCDC' },
    { id: 'explore', label: t('showcase.tabs.explore', 'Explore'), icon: '\uD83D\uDD0D' },
  ]

  // Menu view - 4-tab hub
  if (view === 'menu') {
    return (
      <div className="showcase-overlay" onClick={handleClose}>
        <div className="showcase-modal showcase-modal--menu" onClick={(e) => e.stopPropagation()}>
          <button className="showcase-close" onClick={handleClose}>
            {'\u2715'}
          </button>
          <div className="showcase-menu-header">
            <h2 className="showcase-menu-title">{t('showcase.archiveTitle', 'TRISMEGISTUS')}</h2>
            <div className="showcase-hub-tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  className={`showcase-hub-tab ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="hub-tab-icon">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
          <div className="showcase-menu-body">
            {activeTab === 'era' && (
              <EraTab onEventClick={handleEraEventClick} />
            )}
            {activeTab === 'fgo' && (
              <ShowcaseMenu
                onSelectContent={handleSelectContent}
                onOpenServantPanel={() => setView('servants')}
                alwaysOpen
              />
            )}
            {activeTab === 'reading' && (
              <HistoryTab
                onHistoryClick={(historyId) => {
                  onHistoryClick?.(historyId)
                  handleClose()
                }}
                onCreateHistory={() => {
                  onCreateHistory?.()
                  handleClose()
                }}
              />
            )}
            {activeTab === 'explore' && (
              <PersonTab
                currentYear={currentYear}
                viewportBounds={viewportBounds}
                zoomLevel={zoomLevel}
                onPersonClick={(personId) => {
                  onPersonClick?.(personId)
                  handleClose()
                }}
              />
            )}
          </div>
        </div>
      </div>
    )
  }

  // Servants browser view
  if (view === 'servants') {
    return (
      <div className="showcase-overlay" onClick={handleClose}>
        <div className="showcase-modal showcase-modal--servants" onClick={(e) => e.stopPropagation()}>
          <div className="showcase-nav-bar">
            <button className="showcase-back-btn" onClick={handleBack}>
              {'\u2190'} Back
            </button>
            <span className="showcase-nav-title">Servant Archive</span>
            <button className="showcase-close" onClick={handleClose}>
              {'\u2715'}
            </button>
          </div>
          <div className="showcase-servants-body">
            <ServantTab
              onPersonClick={(personId) => {
                onPersonClick?.(personId)
                handleClose()
              }}
              onFlyToLocation={onFlyToLocation}
              onSetCurrentYear={onSetCurrentYear}
            />
          </div>
        </div>
      </div>
    )
  }

  // Content detail view
  const displayContent = internalContent

  if (!displayContent) {
    // Shouldn't happen in 'content' view, but safety fallback
    setView('menu')
    return null
  }

  const getTypeLabel = () => {
    switch (displayContent.type) {
      case 'singularity': return t('showcase.types.singularity')
      case 'lostbelt': return t('showcase.types.lostbelt')
      case 'servant': return t('showcase.types.servant')
      case 'article': return t('showcase.types.article')
      default: return ''
    }
  }

  const getTypeColor = () => {
    switch (displayContent.type) {
      case 'singularity': return 'var(--chaldea-orange)'
      case 'lostbelt': return 'var(--chaldea-magenta)'
      case 'servant': return 'var(--chaldea-gold)'
      case 'article': return 'var(--chaldea-cyan)'
      default: return 'var(--chaldea-cyan)'
    }
  }

  const renderRarityStars = (rarity: number) => {
    return '★'.repeat(rarity)
  }

  return (
    <div className="showcase-overlay" onClick={handleClose}>
      <div className="showcase-modal" onClick={(e) => e.stopPropagation()}>
        {/* Nav Bar with Back + Close */}
        <div className="showcase-nav-bar">
          <button className="showcase-back-btn" onClick={handleBack}>
            {'\u2190'} Back
          </button>
          <span className="showcase-nav-title">{getTypeLabel()}</span>
          <button className="showcase-close" onClick={handleClose}>
            {'\u2715'}
          </button>
        </div>

        {/* Header */}
        <div className="showcase-header" style={{ borderColor: getTypeColor() }}>
          <div className="showcase-type" style={{ color: getTypeColor() }}>
            <span className="type-icon">{'\u25C8'}</span>
            {getTypeLabel()}
            {displayContent.chapter && <span className="chapter-badge">{displayContent.chapter}</span>}
          </div>
          <h1 className="showcase-title">{displayContent.title}</h1>
          {displayContent.subtitle && (
            <div className="showcase-subtitle">{displayContent.subtitle}</div>
          )}
          <div className="showcase-meta">
            {displayContent.era && <span className="meta-item">{displayContent.era}</span>}
            {displayContent.year && (
              <span className="meta-item">
                {displayContent.year < 0 ? `${Math.abs(displayContent.year)} BC` : `${displayContent.year} AD`}
              </span>
            )}
            {displayContent.location && <span className="meta-item">{displayContent.location}</span>}
          </div>
        </div>

        {/* Content Body */}
        <div className="showcase-body">
          {/* Main Description */}
          <div className="showcase-description">
            {displayContent.description}
          </div>

          {/* Sections */}
          {displayContent.sections?.map((section, idx) => (
            <div key={idx} className="showcase-section">
              <h3 className="section-title">
                <span className="section-marker">{'\u25B8'}</span>
                {section.title}
              </h3>
              <div className="section-content">{section.content}</div>
            </div>
          ))}

          {/* Historical Basis */}
          {displayContent.historicalBasis && (
            <div className="showcase-section historical">
              <h3 className="section-title">
                <span className="section-marker">{'\u25B8'}</span>
                {t('showcase.historicalBasis')}
              </h3>
              <div className="section-content">{displayContent.historicalBasis}</div>
            </div>
          )}

          {/* Related Servants */}
          {displayContent.relatedServants && displayContent.relatedServants.length > 0 && (
            <div className="showcase-section">
              <h3 className="section-title">
                <span className="section-marker">{'\u25B8'}</span>
                {t('showcase.relatedServants')}
              </h3>
              <div className="servant-grid">
                {displayContent.relatedServants.map((servant, idx) => (
                  <div key={idx} className="servant-card">
                    <div className="servant-class">{servant.class}</div>
                    <div className="servant-name">{servant.name}</div>
                    <div className="servant-rarity" style={{ color: 'var(--chaldea-gold)' }}>
                      {renderRarityStars(servant.rarity)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Events */}
          {displayContent.relatedEvents && displayContent.relatedEvents.length > 0 && (
            <div className="showcase-section">
              <h3 className="section-title">
                <span className="section-marker">{'\u25B8'}</span>
                {t('showcase.relatedEvents')}
              </h3>
              <div className="related-events-list">
                {displayContent.relatedEvents.map((event) => (
                  <button
                    key={event.id}
                    className="related-event-btn"
                    onClick={() => onEventClick?.(event.id)}
                  >
                    <span className="event-year">
                      {event.year < 0 ? `${Math.abs(event.year)} BC` : `${event.year} AD`}
                    </span>
                    <span className="event-title">{event.title}</span>
                    <span className="event-arrow">{'\u2192'}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {displayContent.sources && displayContent.sources.length > 0 && (
            <div className="showcase-sources">
              <div className="sources-label">{t('showcase.sources')}</div>
              <div className="sources-list">
                {displayContent.sources.map((source, idx) => (
                  <span key={idx} className="source-item">{source}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="showcase-footer">
          <div className="footer-decoration">
            <span className="deco-line"></span>
            <span className="deco-text">CHALDEAS ARCHIVE</span>
            <span className="deco-line"></span>
          </div>
        </div>
      </div>
    </div>
  )
}
