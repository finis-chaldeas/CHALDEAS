import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { HistoryShift } from '../../types'

interface Props {
  chainType: string
  shifts: HistoryShift[]
  onShiftClick: (shiftId: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

const PREVIEW_COUNT = 8

export function MagazineShiftRow({ chainType, shifts, onShiftClick }: Props) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const label = t(`trismegistos.magazine.${chainType}`) || chainType
  const displayed = expanded ? shifts : shifts.slice(0, PREVIEW_COUNT)

  return (
    <div className="mag-shift-row">
      <div className="mag-shift-row__header">
        <span className="mag-shift-row__label">
          {label} ({shifts.length})
        </span>
        {shifts.length > PREVIEW_COUNT && (
          <button
            className="mag-shift-row__toggle"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? t('trismegistos.magazine.collapse') : t('trismegistos.magazine.viewAll')}
          </button>
        )}
      </div>

      {!expanded ? (
        <div className="mag-shift-row__scroll" ref={scrollRef}>
          {displayed.map((shift) => {
            const title = getLocalizedText(shift, 'title', preferredLanguage)
            return (
              <button
                key={shift.id}
                className="mag-shift-card"
                onClick={() => onShiftClick(shift.id)}
              >
                <div className="mag-shift-card__title">{title}</div>
                <div className="mag-shift-card__meta">
                  {formatYear(shift.year_start)} · {shift.page_count}p
                </div>
              </button>
            )
          })}
        </div>
      ) : (
        <div className="mag-shift-row__list">
          {displayed.map((shift) => {
            const title = getLocalizedText(shift, 'title', preferredLanguage)
            const summary = getLocalizedText(shift, 'summary', preferredLanguage)
            return (
              <button
                key={shift.id}
                className="mag-shift-list-item"
                onClick={() => onShiftClick(shift.id)}
              >
                <div className="mag-shift-list-item__body">
                  <div className="mag-shift-list-item__title">{title}</div>
                  <div className="mag-shift-list-item__meta">
                    {formatYear(shift.year_start)}
                    {shift.year_end ? ` ~ ${formatYear(shift.year_end)}` : ''}
                    {' · '}{shift.page_count}p
                  </div>
                  {summary && (
                    <div className="mag-shift-list-item__summary">{summary}</div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
