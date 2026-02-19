/**
 * TourOverlay - Guided episode tour with auto globe movement
 *
 * Shows a story card at the bottom of the screen while the globe
 * automatically moves to each tour step location. "Netflix for history."
 */
import { useState, useEffect, useCallback } from 'react'
import type { ShebaEpisode, TourStep } from '../../data/shebaEpisodes'
import './tour.css'

interface TourOverlayProps {
  episode: ShebaEpisode
  onClose: () => void
  onFlyToLocation: (lat: number, lng: number) => void
  onSetCurrentYear: (year: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function TourOverlay({
  episode,
  onClose,
  onFlyToLocation,
  onSetCurrentYear,
}: TourOverlayProps) {
  const steps = episode.tourSteps || []
  const [currentStep, setCurrentStep] = useState(0)
  const [isTransitioning, setIsTransitioning] = useState(false)

  const step = steps[currentStep]
  const isFirst = currentStep === 0
  const isLast = currentStep === steps.length - 1
  const progress = steps.length > 1 ? ((currentStep) / (steps.length - 1)) * 100 : 100

  // Navigate globe to current step
  const navigateToStep = useCallback((stepData: TourStep) => {
    setIsTransitioning(true)
    onFlyToLocation(stepData.latitude, stepData.longitude)
    onSetCurrentYear(stepData.year)
    // Allow transition animation
    setTimeout(() => setIsTransitioning(false), 800)
  }, [onFlyToLocation, onSetCurrentYear])

  // Navigate to first step on mount
  useEffect(() => {
    if (steps.length > 0) {
      navigateToStep(steps[0])
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleNext = () => {
    if (isLast) return
    const next = currentStep + 1
    setCurrentStep(next)
    navigateToStep(steps[next])
  }

  const handlePrev = () => {
    if (isFirst) return
    const prev = currentStep - 1
    setCurrentStep(prev)
    navigateToStep(steps[prev])
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        handleNext()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        handlePrev()
      } else if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [currentStep]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!step) return null

  return (
    <div className="tour-overlay">
      {/* Top bar: Episode title + close */}
      <div className="tour-top-bar">
        <div className="tour-episode-title">
          <span className="tour-sheba-icon">{'\u25CE'}</span>
          {episode.title_ko || episode.title}
        </div>
        <button className="tour-close-btn" onClick={onClose} title="Close tour">
          {'\u2715'}
        </button>
      </div>

      {/* Progress bar */}
      <div className="tour-progress-bar">
        <div className="tour-progress-fill" style={{ width: `${progress}%` }} />
        {steps.map((_, i) => (
          <button
            key={i}
            className={`tour-progress-dot ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'passed' : ''}`}
            onClick={() => { setCurrentStep(i); navigateToStep(steps[i]) }}
            style={{ left: `${steps.length > 1 ? (i / (steps.length - 1)) * 100 : 50}%` }}
          />
        ))}
      </div>

      {/* Story card (bottom) */}
      <div className={`tour-card ${isTransitioning ? 'transitioning' : ''}`}>
        <div className="tour-card-step-indicator">
          {currentStep + 1} / {steps.length}
        </div>

        <div className="tour-card-year">{formatYear(step.year)}</div>

        <h3 className="tour-card-title">
          {step.title_ko || step.title}
        </h3>

        <p className="tour-card-description">
          {step.description}
        </p>

        {episode.relatedServants && episode.relatedServants.length > 0 && isFirst && (
          <div className="tour-card-servants">
            {'\u2726'} Related Servants: {episode.relatedServants.join(', ')}
          </div>
        )}

        {/* Navigation buttons */}
        <div className="tour-card-nav">
          <button
            className="tour-nav-btn tour-nav-prev"
            onClick={handlePrev}
            disabled={isFirst}
          >
            {'\u2190'} Previous
          </button>

          {isLast ? (
            <button
              className="tour-nav-btn tour-nav-finish"
              onClick={onClose}
            >
              Finish Tour {'\u2713'}
            </button>
          ) : (
            <button
              className="tour-nav-btn tour-nav-next"
              onClick={handleNext}
            >
              Next {'\u2192'}
            </button>
          )}
        </div>

        <div className="tour-card-hint">
          Use arrow keys or space to navigate
        </div>
      </div>
    </div>
  )
}
