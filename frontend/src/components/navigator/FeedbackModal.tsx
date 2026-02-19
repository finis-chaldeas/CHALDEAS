/**
 * FeedbackModal - User feedback/report form for content issues
 *
 * Allows users to report incorrect, misleading, or missing content.
 * Supports narratives, domain classifications, and importance scores.
 */
import { useState } from 'react'
import { timelineApi } from '../../api/client'

interface FeedbackModalProps {
  targetType: string
  targetId: number
  onClose: () => void
}

const FEEDBACK_TYPES = [
  { value: 'incorrect', label: 'Factually incorrect' },
  { value: 'misleading', label: 'Misleading/biased' },
  { value: 'missing', label: 'Important info missing' },
  { value: 'wrong_domain', label: 'Wrong domain classification' },
  { value: 'wrong_score', label: 'Wrong importance score' },
]

export function FeedbackModal({ targetType, targetId, onClose }: FeedbackModalProps) {
  const [feedbackType, setFeedbackType] = useState('')
  const [description, setDescription] = useState('')
  const [suggestedFix, setSuggestedFix] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!feedbackType) {
      setError('Please select a feedback type.')
      return
    }

    setSubmitting(true)
    setError('')

    try {
      await timelineApi.submitFeedback({
        target_type: targetType,
        target_id: targetId,
        feedback_type: feedbackType,
        description: description || undefined,
        suggested_fix: suggestedFix || undefined,
      })
      setSubmitted(true)
    } catch {
      setError('Failed to submit feedback. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="feedback-modal-overlay" onClick={onClose}>
        <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
          <div className="feedback-success">
            <span className="feedback-success-icon">{'\u2713'}</span>
            <h3>Thank you!</h3>
            <p>Your feedback has been submitted and will be reviewed.</p>
            <button className="feedback-close-btn" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="feedback-modal-overlay" onClick={onClose}>
      <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
        <div className="feedback-header">
          <h3>Report an Issue</h3>
          <button className="feedback-modal-close" onClick={onClose}>{'\u2715'}</button>
        </div>

        <div className="feedback-body">
          <div className="feedback-field">
            <label className="feedback-label">What's wrong?</label>
            <div className="feedback-options">
              {FEEDBACK_TYPES.map((ft) => (
                <label key={ft.value} className="feedback-option">
                  <input
                    type="radio"
                    name="feedbackType"
                    value={ft.value}
                    checked={feedbackType === ft.value}
                    onChange={(e) => setFeedbackType(e.target.value)}
                  />
                  <span>{ft.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="feedback-field">
            <label className="feedback-label">Details (optional)</label>
            <textarea
              className="feedback-textarea"
              placeholder="Describe the issue..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className="feedback-field">
            <label className="feedback-label">Suggested fix (optional)</label>
            <textarea
              className="feedback-textarea"
              placeholder="What should it say instead?"
              value={suggestedFix}
              onChange={(e) => setSuggestedFix(e.target.value)}
              rows={2}
            />
          </div>

          {error && <div className="feedback-error">{error}</div>}
        </div>

        <div className="feedback-footer">
          <button className="feedback-cancel-btn" onClick={onClose}>Cancel</button>
          <button
            className="feedback-submit-btn"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Submitting...' : 'Submit Report'}
          </button>
        </div>
      </div>
    </div>
  )
}
