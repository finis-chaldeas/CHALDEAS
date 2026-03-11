import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Global error boundary — catches render errors and shows a recovery UI
 * instead of a white screen crash.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('CHALDEAS ErrorBoundary caught:', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-boundary-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 className="error-boundary-title">Observation Interrupted</h2>
            <p className="error-boundary-message">
              Something went wrong while rendering. You can try reloading or resetting the view.
            </p>
            <div className="error-boundary-actions">
              <button className="error-boundary-btn primary" onClick={this.handleReload}>
                Reload
              </button>
              <button className="error-boundary-btn" onClick={this.handleReset}>
                Reset View
              </button>
            </div>
            <details className="error-boundary-details">
              <summary>Error details</summary>
              <pre>{this.state.error?.message}</pre>
              <pre>{this.state.error?.stack}</pre>
            </details>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Lightweight error fallback for individual panels.
 * Shows inline error instead of crashing the whole app.
 */
export function PanelErrorFallback({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="panel-error-fallback">
      <p>Failed to load this panel.</p>
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  )
}
