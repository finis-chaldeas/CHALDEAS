import { useEffect, useCallback } from 'react'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore } from '../../store/settingsStore'
import type { ShiftPage } from '../../types'
import WidgetSlot from './widgets/WidgetSlot'
import './widgets'
import './ShiftPanel.css'
import './ShiftWidgets.css'

function formatYear(year: number | undefined | null): string {
  if (year == null) return ''
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function getEraName(year: number): string {
  if (year < -3000) return 'Prehistoric'
  if (year < -500) return 'Ancient'
  if (year < 500) return 'Classical'
  if (year < 1500) return 'Medieval'
  if (year < 1800) return 'Early Modern'
  if (year < 1945) return 'Modern'
  return 'Contemporary'
}

export default function ShiftPanel() {
  const activeShift = useGlobeStore((s) => s.activeShift)
  const activePageIndex = useGlobeStore((s) => s.activePageIndex)
  const closeShift = useGlobeStore((s) => s.closeShift)
  const goToPage = useGlobeStore((s) => s.goToPage)
  const nextPage = useGlobeStore((s) => s.nextPage)
  const prevPage = useGlobeStore((s) => s.prevPage)
  const setCurrentYear = useTimelineStore((s) => s.setCurrentYear)
  const { preferredLanguage } = useSettingsStore()

  const pages = activeShift?.pages || []
  const currentPage: ShiftPage | undefined = pages[activePageIndex]

  useEffect(() => {
    if (currentPage?.year_start != null) {
      setCurrentYear(currentPage.year_start)
    }
  }, [activePageIndex, currentPage?.year_start, setCurrentYear])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!activeShift) return
    if (e.key === 'ArrowRight') { e.preventDefault(); nextPage() }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); prevPage() }
    else if (e.key === 'Escape') { e.preventDefault(); closeShift() }
  }, [activeShift, nextPage, prevPage, closeShift])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (!activeShift || !currentPage) return null

  const pageWidgets = currentPage.widgets || []

  // Language-aware narrative: prefer _ko fields when language is Korean
  const narrativeText = preferredLanguage === 'ko'
    ? (currentPage.page_narrative_ko || currentPage.narrative_ko || currentPage.page_narrative || currentPage.narrative || '')
    : (currentPage.page_narrative || currentPage.narrative || '')
  const shiftTitle = (preferredLanguage === 'ko' && activeShift.title_ko)
    ? activeShift.title_ko : activeShift.title
  const showDots = pages.length <= 25
  const era = getEraName(activeShift.year_start)
  const yearRange = activeShift.year_end
    ? `${formatYear(activeShift.year_start)} ~ ${formatYear(activeShift.year_end)}`
    : formatYear(activeShift.year_start)

  return (
    <>
      {/* ── Top-left: FGO Singularity banner with tail ── */}
      <div className="shift-singularity">
        <div className="shift-singularity-info">
          <div className="shift-singularity-era">{era}</div>
          <div className="shift-singularity-title">{shiftTitle}</div>
          <div className="shift-singularity-year">{yearRange}</div>
        </div>
        <button className="shift-singularity-close" onClick={closeShift}>{'\u2715'}</button>
      </div>

      {/* ── Widget slots ── */}
      {pageWidgets.length > 0 && <>
        <WidgetSlot widgets={pageWidgets} position="left" />
        <WidgetSlot widgets={pageWidgets} position="right" />
        <WidgetSlot widgets={pageWidgets} position="overlay" />
      </>}

      {/* ── Bottom: text + navigation ── */}
      {pageWidgets.length > 0 && (
        <WidgetSlot widgets={pageWidgets} position="bottom" />
      )}

      <div className="shift-bottom">
        <div className="shift-bottom-inner">
          {/* Current page info */}
          <div className="shift-page-info">
            {currentPage.year_start != null && (
              <span className="shift-page-year">{formatYear(currentPage.year_start)}</span>
            )}
            {currentPage.title && (
              <h3 className="shift-page-title">
                {(preferredLanguage === 'ko' && currentPage.title_ko) ? currentPage.title_ko : currentPage.title}
              </h3>
            )}
            {narrativeText && (
              <p className="shift-page-text">{narrativeText}</p>
            )}
          </div>

          {/* Navigation */}
          <div className="shift-nav">
            <button className="shift-nav-btn" onClick={prevPage} disabled={activePageIndex === 0}>
              &larr;
            </button>

            {showDots ? (
              <div className="shift-dots">
                {pages.map((_, i) => (
                  <button
                    key={i}
                    className={`shift-dot ${i === activePageIndex ? 'active' : i < activePageIndex ? 'visited' : ''}`}
                    onClick={() => goToPage(i)}
                  />
                ))}
              </div>
            ) : (
              <div className="shift-counter">
                <span className="current">{activePageIndex + 1}</span> / {pages.length}
              </div>
            )}

            <button className="shift-nav-btn" onClick={nextPage} disabled={activePageIndex >= pages.length - 1}>
              &rarr;
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
