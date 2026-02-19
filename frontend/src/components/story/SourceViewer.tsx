/**
 * SourceViewer - Display source content (Wikipedia, etc.)
 *
 * Fetches and displays:
 * - Wikipedia articles from local ZIM file
 * - Other source content
 * - External links when local content unavailable
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'

interface SourceViewerProps {
  sourceId: number
  onClose: () => void
}

interface WikipediaContent {
  source_id: number
  title: string
  content_html: string | null
  content_text: string | null
  word_count?: number
  external_url: string
  status: string
}

export function SourceViewer({ sourceId, onClose }: SourceViewerProps) {
  const { t } = useTranslation()
  const [showHtml, setShowHtml] = useState(false)

  const { data: content, isLoading, error } = useQuery({
    queryKey: ['source-content', sourceId],
    queryFn: () => api.get(`/sources/wiki/${sourceId}`),
    select: (res) => res.data as WikipediaContent,
    retry: false,
  })

  return (
    <div className="source-viewer">
      {/* Header */}
      <div className="source-viewer-header">
        <div className="source-viewer-title">
          <span className="source-icon">📖</span>
          {content?.title || t('source.loading', 'Loading...')}
        </div>
        <button className="source-viewer-close" onClick={onClose}>✕</button>
      </div>

      {/* Content */}
      <div className="source-viewer-content">
        {isLoading && (
          <div className="source-loading">
            <div className="source-loading-spinner" />
            <span>{t('source.fetchingContent', 'Fetching content...')}</span>
          </div>
        )}

        {error && (
          <div className="source-error">
            <span className="error-icon">⚠️</span>
            <span>{t('source.errorLoading', 'Failed to load source content')}</span>
          </div>
        )}

        {content && (
          <>
            {/* Status messages */}
            {content.status !== 'ok' && (
              <div className="source-status">
                {content.status === 'zim_not_found' && (
                  <span>{t('source.zimNotFound', 'Local Wikipedia archive not available')}</span>
                )}
                {content.status === 'article_not_found' && (
                  <span>{t('source.articleNotFound', 'Article not found in local archive')}</span>
                )}
                {content.status === 'libzim_not_installed' && (
                  <span>{t('source.libzimNotInstalled', 'ZIM reader not installed')}</span>
                )}
                {content.status.startsWith('error:') && (
                  <span>{content.status}</span>
                )}
              </div>
            )}

            {/* Word count */}
            {content.word_count && (
              <div className="source-meta">
                <span>{content.word_count.toLocaleString()} words</span>
              </div>
            )}

            {/* Toggle HTML/Text view */}
            {content.content_html && content.content_text && (
              <div className="source-view-toggle">
                <button
                  className={`view-btn ${!showHtml ? 'active' : ''}`}
                  onClick={() => setShowHtml(false)}
                >
                  {t('source.textView', 'Text')}
                </button>
                <button
                  className={`view-btn ${showHtml ? 'active' : ''}`}
                  onClick={() => setShowHtml(true)}
                >
                  {t('source.htmlView', 'Formatted')}
                </button>
              </div>
            )}

            {/* Content display */}
            {showHtml && content.content_html ? (
              <div
                className="source-html"
                dangerouslySetInnerHTML={{ __html: content.content_html }}
              />
            ) : content.content_text ? (
              <div className="source-text">
                {content.content_text}
              </div>
            ) : null}

            {/* External link */}
            {content.external_url && (
              <div className="source-external">
                <a
                  href={content.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-external-link"
                >
                  {t('source.viewOnWikipedia', 'View on Wikipedia')} →
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default SourceViewer
