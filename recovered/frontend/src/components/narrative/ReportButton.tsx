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
      <button
        onClick={() => setOpen(true)}
        className="text-[10px] text-chaldea-text hover:text-chaldea-orange transition-colors"
      >
        Report Issue
      </button>
    )
  }

  if (submitted) {
    return (
      <div className="text-[10px] text-chaldea-green py-2">
        Report submitted. Thank you.
      </div>
    )
  }

  return (
    <div className="border border-chaldea-border rounded p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-chaldea-text">
          Report Issue
        </span>
        <button
          onClick={() => setOpen(false)}
          className="text-chaldea-text hover:text-chaldea-text-bright text-xs"
        >
          x
        </button>
      </div>
      <select
        value={reportType}
        onChange={(e) => setReportType(e.target.value as ContentReport['report_type'])}
        className="w-full text-xs bg-chaldea-bg border border-chaldea-border rounded px-2 py-1
                   text-chaldea-text-bright focus:border-chaldea-cyan outline-none"
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
        className="w-full text-xs bg-chaldea-bg border border-chaldea-border rounded px-2 py-1
                   text-chaldea-text-bright placeholder:text-chaldea-text/50 focus:border-chaldea-cyan
                   outline-none resize-none"
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
        className="text-xs px-3 py-1 rounded border border-chaldea-orange text-chaldea-orange
                   hover:bg-chaldea-orange/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? 'Submitting...' : 'Submit'}
      </button>
    </div>
  )
}
