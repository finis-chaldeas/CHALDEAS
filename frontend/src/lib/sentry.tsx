/**
 * Sentry initialization for error tracking
 *
 * Set VITE_SENTRY_DSN in .env to enable error tracking.
 * Get your DSN from: https://sentry.io
 */
import * as Sentry from '@sentry/react'

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN

  if (!dsn) {
    if (import.meta.env.DEV) {
      console.log('[Sentry] DSN not configured, error tracking disabled')
    }
    return
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    enabled: import.meta.env.PROD,

    // Performance monitoring
    integrations: [
      Sentry.browserTracingIntegration(),
    ],

    tracesSampleRate: 0.1,

    // Ignore common non-actionable errors
    ignoreErrors: [
      'Network Error',
      'Failed to fetch',
      'NetworkError',
      'Load failed',
      /^chrome-extension:\/\//,
      /^moz-extension:\/\//,
      'ResizeObserver loop',
      'WebGL context lost',
    ],
  })

  console.log('[Sentry] Initialized for', import.meta.env.MODE)
}

// Error boundary fallback component - matches Sentry's FallbackRender interface
interface ErrorFallbackProps {
  error: unknown
  componentStack: string
  eventId: string
  resetError: () => void
}

export function ErrorFallback({ error, resetError }: ErrorFallbackProps) {
  const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'

  return (
    <div style={{
      padding: '2rem',
      textAlign: 'center',
      background: '#1a1a2e',
      color: '#fff',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <h1 style={{ color: '#ef4444', marginBottom: '1rem' }}>Something went wrong</h1>
      <p style={{ color: '#888', marginBottom: '1rem' }}>
        {errorMessage}
      </p>
      <button
        onClick={resetError}
        style={{
          padding: '0.75rem 1.5rem',
          background: '#00d4ff',
          border: 'none',
          borderRadius: '6px',
          color: '#000',
          fontWeight: 500,
          cursor: 'pointer',
        }}
      >
        Try again
      </button>
    </div>
  )
}

// Re-export Sentry utilities
export { Sentry }
