import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { reportsApi } from '../../api/client'
import type { ContentReport } from '../../types'

interface ReportButtonProps {
  entityType: string
  entityId: number
}

export function ReportButton({ entityType, entityId }: ReportButtonProps) {
  const [open, setOpen] = useState(false)
  const [reportType, setReportType] = useState<ContentReport['report_type']>('incorrect')
  const [reason, setReason] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const mutation = useMutation({
    mutationFn: (data: {
      entity_type: string
      entity_id: number
      report_type: string
      reason: string
    }) => reportsApi.submit(data),
    onSuccess: () => {
      setSubmitted(true)
      setTimeout(() => {
        setOpen(false)
        setSubmitted(false)
        setReason('')
      }, 2000)
    },
  })

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="nc-report-btn">
        Report Issue
      </button>
    )
  }

  if (submitted) {
    return <div className="nc-report-success">Report submitted. Thank you.</div>
  }

  return (
    <div className="nc-report-form">
      <div className="nc-report-header">
        <span className="nc-report-label">Report Issue</span>
        <button onClick={() => setOpen(false)} className="nc-report-close">x</button>
      </div>
      <select
        value={reportType}
        onChange={(e) => setReportType(e.target.value as ContentReport['report_type'])}
        className="nc-report-select"
      >
        <option value="incorrect">Incorrect information</option>
        <option value="suspicious">Suspicious / unverified</option>
        <option value="low_quality">Low quality</option>
        <option value="inappropriate">Inappropriate</option>
        <option value="other">Other</option>
      </select>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Describe the issue..."
        rows={2}
        className="nc-report-textarea"
      />
      <button
        onClick={() =>
          mutation.mutate({
            entity_type: entityType,
            entity_id: entityId,
            report_type: reportType,
            reason,
          })
        }
        disabled={!reason.trim() || mutation.isPending}
        className="nc-report-submit"
      >
        {mutation.isPending ? 'Submitting...' : 'Submit'}
      </button>
    </div>
  )
}
