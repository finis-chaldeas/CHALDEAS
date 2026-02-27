import { Suspense } from 'react'
import type { PageWidget } from '../../../types'
import { useSettingsStore } from '../../../store/settingsStore'
import { getWidgetComponent } from './registry'

export default function WidgetRenderer({ widget }: { widget: PageWidget }) {
  const Component = getWidgetComponent(widget.type)
  const lang = useSettingsStore((s) => s.preferredLanguage)
  if (!Component) return null
  return (
    <Suspense fallback={null}>
      <Component data={widget.data} slot={widget.slot} lang={lang} />
    </Suspense>
  )
}
