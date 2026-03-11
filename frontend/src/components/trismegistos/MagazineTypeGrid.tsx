import { useTranslation } from 'react-i18next'

interface TypeCount {
  type: string
  count: number
}

interface Props {
  typeCounts: TypeCount[]
}

export function MagazineTypeGrid({ typeCounts }: Props) {
  const { t } = useTranslation()

  return (
    <div className="mag-type-grid">
      {typeCounts.filter(tc => tc.count > 0).map(({ type, count }) => (
        <div key={type} className="mag-type-tile">
          <div className="mag-type-tile__label">
            {t(`trismegistos.magazine.${type}`) || type}
          </div>
          <div className="mag-type-tile__count">
            {count} {t('trismegistos.magazine.shifts')}
          </div>
        </div>
      ))}
    </div>
  )
}
