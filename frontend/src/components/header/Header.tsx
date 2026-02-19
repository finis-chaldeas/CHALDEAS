/**
 * Header - Main application header
 *
 * Contains:
 * - Logo
 * - Search bar
 * - Language selector
 * - Settings button
 */
import { useTranslation } from 'react-i18next'
import { SearchAutocomplete } from '../search'
import { LanguageSelector } from '../common'

interface HeaderProps {
  onSelectEvent: (eventId: number) => Promise<void>
  onSelectPerson: (personId: number) => void
  onSelectLocation: (locationId: number) => void
  onSearch: (query: string) => void
  onSettingsClick: () => void
}

export function Header({
  onSelectEvent,
  onSelectPerson,
  onSelectLocation,
  onSearch,
  onSettingsClick
}: HeaderProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Logo */}
      <div className="logo">
        <div className="logo-icon">⊕</div>
        <div className="logo-text">{t('app.name')}</div>
      </div>

      {/* Search */}
      <div className="search-wrapper">
        <SearchAutocomplete
          placeholder={t('sidebar.searchPlaceholder')}
          onSelectEvent={onSelectEvent}
          onSelectPerson={onSelectPerson}
          onSelectLocation={onSelectLocation}
          onSearch={onSearch}
        />
      </div>

      {/* Actions */}
      <div className="header-actions">
        <LanguageSelector />
        <button
          className="header-btn"
          onClick={onSettingsClick}
          title={t('settings.title', 'Settings')}
        >
          ⚙
        </button>
      </div>
    </>
  )
}

export default Header
