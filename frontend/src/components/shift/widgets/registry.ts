import { ComponentType, lazy } from 'react'

export interface WidgetProps {
  data: Record<string, unknown>
  slot: string
  lang: string
}

/** Pick localized value: checks data[key + '_' + lang] first, falls back to data[key]. */
export function loc(data: Record<string, unknown>, key: string, lang: string): string {
  if (lang !== 'en') {
    const localized = data[`${key}_${lang}`]
    if (typeof localized === 'string' && localized) return localized
  }
  const val = data[key]
  return typeof val === 'string' ? val : ''
}

/** Pick localized array: checks data[key + '_' + lang] first, falls back to data[key]. */
export function locArray(data: Record<string, unknown>, key: string, lang: string): string[] | undefined {
  if (lang !== 'en') {
    const localized = data[`${key}_${lang}`]
    if (Array.isArray(localized) && localized.length > 0) return localized as string[]
  }
  const val = data[key]
  return Array.isArray(val) ? val as string[] : undefined
}

const widgetRegistry = new Map<string, ComponentType<WidgetProps>>()

export function registerWidget(type: string, component: ComponentType<WidgetProps>): void {
  widgetRegistry.set(type, component)
}

export function getWidgetComponent(type: string): ComponentType<WidgetProps> | undefined {
  return widgetRegistry.get(type)
}

export function registerLazyWidget(
  type: string,
  factory: () => Promise<{ default: ComponentType<WidgetProps> }>,
): void {
  widgetRegistry.set(type, lazy(factory))
}
