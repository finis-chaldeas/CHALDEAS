import { useTranslation } from 'react-i18next'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PeriodSummary } from '../../types'
import { PeriodDetail } from './PeriodDetail'

interface Props {
  period: PeriodSummary
  isExpanded: boolean
  onToggle: () => void
  onGlobeView: (year: number) => void
  onShiftClick: (shiftId: number) => void
  onEventClick: (eventId: number) => void
  onPersonClick: (personId: number) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function PeriodCard({
  period,
  isExpanded,
  onToggle,
  onGlobeView,
  onShiftClick,
  onEventClick,
  onPersonClick,
}: Props) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()

  const headline = getLocalizedText(period, 'headline', preferredLanguage)
  const yearRange = `${formatYear(period.period_start)} ~ ${formatYear(period.period_end)}`

  return (
    <div className={`era-period-card ${isExpanded ? 'era-period-card--expanded' : ''}`}>
      <button className="era-period-card__header" onClick={onToggle}>
        <div className="era-period-card__header-left">
          <div className="era-period-card__years">{yearRange}</div>
          {headline && (
            <div className="era-period-card__headline">{headline}</div>
          )}
        </div>
        <div className="era-period-card__header-right">
          <span className="era-period-card__stats">
            {period.event_count.toLocaleString()} {t('trismegistos.era.events')}
            {' · '}
            {period.person_count.toLocaleString()} {t('trismegistos.era.persons')}
          </span>
          <span className={`era-period-card__toggle ${isExpanded ? 'era-period-card__toggle--open' : ''}`}>
            {'\u25BC'}
          </span>
        </div>
      </button>

      {isExpanded && (
        <PeriodDetail
          periodStart={period.period_start}
          periodEnd={period.period_end}
          onGlobeView={onGlobeView}
          onShiftClick={onShiftClick}
          onEventClick={onEventClick}
          onPersonClick={onPersonClick}
        />
      )}
    </div>
  )
}
