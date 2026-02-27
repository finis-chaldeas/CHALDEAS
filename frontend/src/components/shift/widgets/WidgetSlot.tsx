import type { PageWidget, WidgetSlotPosition } from '../../../types'
import WidgetRenderer from './WidgetRenderer'

interface WidgetSlotProps {
  widgets: PageWidget[]
  position: WidgetSlotPosition
}

export default function WidgetSlot({ widgets, position }: WidgetSlotProps) {
  const filtered = widgets
    .filter((w) => w.slot === position)
    .sort((a, b) => (a.priority ?? 10) - (b.priority ?? 10))

  if (filtered.length === 0) return null

  return (
    <div className={`widget-slot widget-slot--${position}`}>
      {filtered.map((w, i) => (
        <WidgetRenderer key={`${w.type}-${i}`} widget={w} />
      ))}
    </div>
  )
}
