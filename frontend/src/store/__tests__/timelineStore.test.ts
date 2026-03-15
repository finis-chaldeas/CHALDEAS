import { describe, it, expect, beforeEach } from 'vitest'
import { useTimelineStore } from '../timelineStore'

// Reset store state before each test
beforeEach(() => {
  useTimelineStore.setState({
    currentYear: -500,
    yearRange: { min: -3000, max: 2024 },
    isPlaying: false,
    playbackSpeed: 10,
    displayMode: 'standard',
  })
})

describe('timelineStore', () => {
  it('has correct initial state', () => {
    const state = useTimelineStore.getState()
    expect(state.currentYear).toBe(-500)
    expect(state.yearRange).toEqual({ min: -3000, max: 2024 })
    expect(state.isPlaying).toBe(false)
    expect(state.playbackSpeed).toBe(10)
    expect(state.displayMode).toBe('standard')
  })

  it('setCurrentYear with number', () => {
    useTimelineStore.getState().setCurrentYear(100)
    expect(useTimelineStore.getState().currentYear).toBe(100)
  })

  it('setCurrentYear with updater function', () => {
    useTimelineStore.getState().setCurrentYear((prev) => prev + 50)
    expect(useTimelineStore.getState().currentYear).toBe(-450)
  })

  it('setYearRange', () => {
    useTimelineStore.getState().setYearRange(-1000, 1000)
    const { yearRange } = useTimelineStore.getState()
    expect(yearRange.min).toBe(-1000)
    expect(yearRange.max).toBe(1000)
  })

  it('play and pause', () => {
    useTimelineStore.getState().play()
    expect(useTimelineStore.getState().isPlaying).toBe(true)

    useTimelineStore.getState().pause()
    expect(useTimelineStore.getState().isPlaying).toBe(false)
  })

  it('setPlaybackSpeed', () => {
    useTimelineStore.getState().setPlaybackSpeed(50)
    expect(useTimelineStore.getState().playbackSpeed).toBe(50)
  })

  it('jumpToEra sets year and pauses', () => {
    useTimelineStore.getState().play()
    useTimelineStore.getState().jumpToEra(1500)
    const state = useTimelineStore.getState()
    expect(state.currentYear).toBe(1500)
    expect(state.isPlaying).toBe(false)
  })

  it('setDisplayMode', () => {
    useTimelineStore.getState().setDisplayMode('expanded')
    expect(useTimelineStore.getState().displayMode).toBe('expanded')
  })

  it('handles BCE dates (negative numbers)', () => {
    useTimelineStore.getState().setCurrentYear(-490)
    expect(useTimelineStore.getState().currentYear).toBe(-490)
  })
})
