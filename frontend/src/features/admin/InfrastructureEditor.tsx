import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../services/api'
import type { Infrastructure } from '../../services/api'
import { Button } from '../../components/ui'

export function InfrastructureEditor({
  item,
  onSaved,
}: {
  item: Infrastructure
  onSaved: () => void
}) {
  const queryClient = useQueryClient()
  const [availability, setAvailability] = useState(item.availability)
  const [verification, setVerification] = useState(item.verification)
  const [provenance, setProvenance] = useState(item.provenance)
  const [reason, setReason] = useState('')
  const mutation = useMutation({
    mutationFn: () =>
      api.editInfrastructure(item.id, {
        expected_version: item.row_version,
        availability,
        verification,
        provenance,
        reason,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['infrastructure'] }),
        queryClient.invalidateQueries({ queryKey: ['graph'] }),
      ])
      onSaved()
    },
  })
  return (
    <form
      className="admin-edit-form"
      onSubmit={(event) => {
        event.preventDefault()
        mutation.mutate()
      }}
    >
      <div className="field">
        <label htmlFor="availability">Availability</label>
        <select
          id="availability"
          value={availability}
          onChange={(event) => setAvailability(event.target.value as typeof availability)}
        >
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="temporarily_blocked">Temporarily blocked</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="verification">Observation status</label>
        <select
          id="verification"
          value={verification}
          onChange={(event) => setVerification(event.target.value as typeof verification)}
        >
          <option value="verified">Verified observation</option>
          <option value="unverified">Unverified</option>
          <option value="needs_review">Needs review</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="provenance">Observation source</label>
        <textarea
          id="provenance"
          value={provenance}
          onChange={(event) => setProvenance(event.target.value)}
          required={verification === 'verified'}
          maxLength={2000}
          rows={3}
        />
      </div>
      <div className="field">
        <label htmlFor="reason">Reason for this change</label>
        <input
          id="reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          required
          minLength={3}
          maxLength={500}
        />
      </div>
      <p className="helper">
        This updates the record and its mapped pathways’ graph revision. It does not certify a route
        as safe.
      </p>
      {mutation.error && (
        <div role="alert" className="form-error-box">
          {mutation.error instanceof ApiError && mutation.error.status === 409
            ? 'Someone updated this record first. This edit was not applied. Close this dialog, refresh the records, and review the latest values before trying again.'
            : mutation.error.message}
        </div>
      )}
      <Button type="submit" busy={mutation.isPending}>
        Save infrastructure change
      </Button>
    </form>
  )
}
