import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'
import { useSettingsStore } from '../../store/settingsStore'
import { portalApi } from '../../api/client'
import type { CollectionDetail } from '../../types'

interface Props {
  onOpenShift: (shiftId: number) => void
}

export function FgoShiftList({ onOpenShift }: Props) {
  const { t } = useTranslation()
  const close = usePortalStore((s) => s.close)
  const { preferredLanguage } = useSettingsStore()

  // Fetch the FGO history bridge collection which contains FGO-linked shifts
  const { data: collection, isLoading } = useQuery<CollectionDetail>({
    queryKey: ['portal-collection', 'fgo-history-bridge'],
    queryFn: async () => {
      const res = await portalApi.getCollection('fgo-history-bridge')
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="fgo-shifts">
        <div className="portal-skeleton" style={{ height: 48, marginBottom: 8 }} />
        <div className="portal-skeleton" style={{ height: 48, marginBottom: 8 }} />
        <div className="portal-skeleton" style={{ height: 48, marginBottom: 8 }} />
      </div>
    )
  }

  // Extract shift entries from collection
  const shiftEntries = (collection?.entries || []).filter(
    (e) => e.entry_type === 'shift' && e.shift_summary
  )

  if (!shiftEntries.length) {
    return (
      <div className="fgo-shifts">
        <div className="fgo-shifts__empty">{t('trismegistos.fgo.noShifts')}</div>
      </div>
    )
  }

  return (
    <div className="fgo-shifts">
      <div className="fgo-shifts__label">{t('trismegistos.fgo.linkedShifts')}</div>
      <div className="fgo-shifts__list">
        {shiftEntries.map((entry) => {
          const shift = entry.shift_summary!
          const title = preferredLanguage === 'ko' && shift.title_ko
            ? shift.title_ko
            : shift.title
          const meta = [
            shift.segment_count ? `${shift.segment_count} ${t('trismegistos.pages')}` : null,
            shift.chain_type ? shift.chain_type.replace('_', ' ') : null,
          ].filter(Boolean).join(' \u00B7 ')

          return (
            <button
              key={shift.id}
              className="fgo-shifts__card"
              onClick={() => { close(); onOpenShift(shift.id) }}
            >
              <span className="fgo-shifts__icon">{'\u25B6'}</span>
              <span className="fgo-shifts__body">
                <span className="fgo-shifts__title">{title}</span>
                {meta && <span className="fgo-shifts__meta">{meta}</span>}
                {entry.note && (
                  <span className="fgo-shifts__note">
                    {preferredLanguage === 'ko' && entry.note_ko ? entry.note_ko : entry.note}
                  </span>
                )}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
