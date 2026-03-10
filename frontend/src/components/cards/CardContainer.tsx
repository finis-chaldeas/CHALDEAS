import { useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import type { CardType, CardMode } from './useCardPopup'
import './cards.css'

interface CardContainerProps {
  type: CardType
  mode: CardMode
  position?: { x: number; y: number } | null
  onClose: () => void
  onExpand?: () => void
  children: React.ReactNode
}

export default function CardContainer({
  type,
  mode,
  position,
  onClose,
  onExpand,
  children,
}: CardContainerProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  const style: React.CSSProperties = position
    ? { left: position.x, top: position.y }
    : {}

  return createPortal(
    <div className="card-overlay" onClick={handleBackdropClick}>
      <div
        className={`card card--${type} card--${mode}`}
        style={style}
      >
        <div className="card-header">
          {mode === 'compact' && onExpand && (
            <button className="card-header__expand" onClick={onExpand}>
              {'\u2197'}
            </button>
          )}
          <button className="card-header__close" onClick={onClose}>
            {'\u2715'}
          </button>
        </div>
        <div className="card-body">{children}</div>
      </div>
    </div>,
    document.body
  )
}
