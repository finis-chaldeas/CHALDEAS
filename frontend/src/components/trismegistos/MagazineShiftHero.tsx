import { useTranslation } from 'react-i18next'
import { useSettingsStore, getLocalizedText } from '../../store/settingsStore'
import type { HistoryShift } from '../../types'

interface Props {
  shift: HistoryShift
  onStart: () => void
  onGlobeView: () => void
}

function formatYear(year: number): string {
  if (year < 0) return `${Math.abs(year)} BCE`
  return `${year} CE`
}

function formatChainType(type: string, t: (key: string) => string): string {
  return t(`trismegistos.magazine.${type}`) || type
}

export function MagazineShiftHero({ shift, onStart, onGlobeView }: Props) {
  const { t } = useTranslation()
  const { preferredLanguage } = useSettingsStore()

  const title = getLocalizedText(shift, 'title', preferredLanguage)
  const summary = getLocalizedText(shift, 'summary', preferredLanguage)
  const yearRange = shift.year_end
    ? `${formatYear(shift.year_start)} ~ ${formatYear(shift.year_end)}`
    : formatYear(shift.year_start)

  return (
    <div className="mag-hero">
      <div className="mag-hero__badge">
        {formatChainType(shift.chain_type, t)}
      </div>
      <h2 className="mag-hero__title">{title}</h2>
      <div className="mag-hero__meta">
        {yearRange} · {shift.page_count}{t('trismegistos.magazine.pages')}
      </div>
      {summary && (
        <p className="mag-hero__excerpt">{summary}</p>
      )}
      <div className="mag-hero__actions">
        <button className="portal-btn portal-btn--primary" onClick={onStart}>
          {t('trismegistos.magazine.startShift')}
        </button>
        <button className="portal-btn portal-btn--secondary" onClick={onGlobeView}>
          {t('trismegistos.magazine.globeView')}
        </button>
      </div>
    </div>
  )
}
