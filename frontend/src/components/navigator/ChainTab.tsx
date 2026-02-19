/**
 * ChainTab - Historical chains (connections) overview
 */
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'

interface ChainStats {
  total_connections: number
  by_layer: {
    person: number
    location: number
    causal: number
    temporal: number
  }
}

export function ChainTab() {
  const { t } = useTranslation()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['chain-stats'],
    queryFn: () => api.get('/chains/stats'),
    select: (res) => res.data as ChainStats,
    staleTime: 60000,
  })

  return (
    <div className="navigator-tab-content">
      <div className="chain-overview">
        <h3 className="chain-overview-title">
          {t('navigator.chainOverview', 'Historical Chain')}
        </h3>

        {isLoading ? (
          <div className="navigator-loading">{t('common.loading', 'Loading...')}</div>
        ) : stats ? (
          <>
            <div className="chain-total">
              <span className="chain-total-value">
                {stats.total_connections?.toLocaleString() || 0}
              </span>
              <span className="chain-total-label">
                {t('navigator.totalConnections', 'Total Connections')}
              </span>
            </div>

            <div className="chain-breakdown">
              <div className="chain-breakdown-item">
                <span className="chain-breakdown-icon">👤</span>
                <span className="chain-breakdown-label">{t('navigator.personChains', 'Person')}</span>
                <span className="chain-breakdown-value">
                  {stats.by_layer?.person?.toLocaleString() || 0}
                </span>
              </div>
              <div className="chain-breakdown-item">
                <span className="chain-breakdown-icon">📍</span>
                <span className="chain-breakdown-label">{t('navigator.locationChains', 'Location')}</span>
                <span className="chain-breakdown-value">
                  {stats.by_layer?.location?.toLocaleString() || 0}
                </span>
              </div>
              <div className="chain-breakdown-item">
                <span className="chain-breakdown-icon">🔗</span>
                <span className="chain-breakdown-label">{t('navigator.causalChains', 'Causal')}</span>
                <span className="chain-breakdown-value">
                  {stats.by_layer?.causal?.toLocaleString() || 0}
                </span>
              </div>
              <div className="chain-breakdown-item">
                <span className="chain-breakdown-icon">⏱️</span>
                <span className="chain-breakdown-label">{t('navigator.temporalChains', 'Temporal')}</span>
                <span className="chain-breakdown-value">
                  {stats.by_layer?.temporal?.toLocaleString() || 0}
                </span>
              </div>
            </div>
          </>
        ) : (
          <div className="navigator-empty">
            {t('navigator.noChainData', 'No chain data available')}
          </div>
        )}
      </div>
    </div>
  )
}
