import { useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useGlobeStore } from '../../store/globeStore'
import { useTimelineStore } from '../../store/timelineStore'
import { useSettingsStore, getEffectiveLanguage } from '../../store/settingsStore'
import { usePortalStore } from '../../store/portalStore'
import { portalApi } from '../../api/client'
import type { ShiftPage, PortalItemSummary } from '../../types'
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
  const lang = getEffectiveLanguage(preferredLanguage)

  const pages = activeShift?.pages || []
  const currentPage: ShiftPage | undefined = pages[activePageIndex]

  // Check if this shift has related portal articles
  const { data: portalItems } = useQuery<PortalItemSummary[]>({
    queryKey: ['portal-items-by-shift', activeShift?.id],
    queryFn: async () => {
      const res = await portalApi.getItemsByShift(activeShift!.id)
      return res.data
    },
    enabled: !!activeShift?.id,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const handleOpenInPortal = () => {
    if (!portalItems || portalItems.length === 0) return
    const slug = portalItems[0].slug
    const { lat, lng } = useGlobeStore.getState().cameraPosition
    const year = useTimelineStore.getState().currentYear
    const store = usePortalStore.getState()
    closeShift()
    store.open({ lat, lng, year })
    store.pushDetail(slug)
  }

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

  // Language-aware narrative: prefer localized fields, fall back to English
  const narrativeText = (() => {
    if (lang === 'ko') return currentPage.page_narrative_ko || currentPage.narrative_ko || currentPage.page_narrative || currentPage.narrative || ''
    if (lang === 'ja') return currentPage.page_narrative_ja || currentPage.narrative_ja || currentPage.page_narrative || currentPage.narrative || ''
    return currentPage.page_narrative || currentPage.narrative || ''
  })()
  const shiftTitle = (() => {
    if (lang === 'ko' && activeShift.title_ko) return activeShift.title_ko
    if (lang === 'ja' && activeShift.title_ja) return activeShift.title_ja
    return activeShift.title
  })()
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
        <div className="shift-singularity-actions">
          {portalItems && portalItems.length > 0 && (
            <button className="shift-portal-link" onClick={handleOpenInPortal}>
              {'\u2726'} Portal
            </button>
          )}
          <button className="shift-singularity-close" onClick={closeShift}>{'\u2715'}</button>
        </div>
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
                {(lang === 'ko' && currentPage.title_ko) ? currentPage.title_ko
                  : (lang === 'ja' && currentPage.title_ja) ? currentPage.title_ja
                  : currentPage.title}
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
