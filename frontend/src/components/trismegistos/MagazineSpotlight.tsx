import { useTranslation } from 'react-i18next'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { PeriodSummary } from '../../types'

interface Props {
  periods: PeriodSummary[]
  onSpotlightClick: (eraId: string) => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

export function MagazineSpotlight({ periods, onSpotlightClick }: Props) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()

  return (
    <div className="mag-spotlight">
      {periods.map((period) => {
        const headline = getLocalizedText(period, 'headline', preferredLanguage)
        const eraId = period.era_id || 'all'

        return (
          <button
            key={period.period_start}
            className="mag-spotlight__card"
            onClick={() => onSpotlightClick(eraId)}
          >
            <div className="mag-spotlight__era">
              {period.era_id ? t(`trismegistos.era.${period.era_id}`, period.era_id) : ''}
            </div>
            <div className="mag-spotlight__headline">
              {headline || `${formatYear(period.period_start)} ~ ${formatYear(period.period_end)}`}
            </div>
            <div className="mag-spotlight__stats">
              {period.event_count.toLocaleString()} {t('trismegistos.magazine.events')}
              {' · '}
              {period.person_count.toLocaleString()} {t('trismegistos.magazine.persons')}
            </div>
          </button>
        )
      })}
    </div>
  )
}
