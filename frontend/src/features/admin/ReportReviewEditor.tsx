import { useRef, useState } from 'react'
import { api } from '../../services/api'
import type { Edge, Infrastructure, Report, ReportReview } from '../../services/api'
import { Badge, Button } from '../../components/ui'
import { ReportCard } from '../reports/ReportCard'
import { requestKey } from '../reports/report-ui'

function pathwayLabel(edge: Edge) {
  return `${edge.has_stairs ? 'Steps walkway' : edge.has_ramp ? 'Ramp walkway' : 'Campus pathway'} · ${edge.distance_m.toFixed(1)} m`
}

export function ReportReviewEditor({
  report,
  edges,
  infrastructure,
  onSaved,
}: {
  report: Report
  edges: Edge[]
  infrastructure: Infrastructure[]
  onSaved: (report: Report) => void
}) {
  const [reason, setReason] = useState('')
  const [search, setSearch] = useState('')
  const [kind, setKind] =
    useState<NonNullable<ReportReview['restriction_kind']>>('temporarily_blocked')
  const [confirmed, setConfirmed] = useState<string[]>(
    report.suggested_edge_ids.length
      ? report.suggested_edge_ids
      : (infrastructure.find((item) => item.id === report.infrastructure_id)?.edge_ids ?? []),
  )
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const keys = useRef<{ body: string; key: string } | null>(null)
  const candidates = edges.filter((edge) =>
    pathwayLabel(edge).toLowerCase().includes(search.toLowerCase()),
  )
  async function decide(action: 'verify' | 'reject' | 'resolve') {
    setPending(true)
    setError('')
    try {
      if (action === 'resolve') {
        const body = { expected_version: report.row_version, reason: reason.trim() }
        onSaved(await api.resolveReport(report.id, body, requestKey(keys, body)))
      } else {
        const body: ReportReview = {
          expected_version: report.row_version,
          decision: action,
          confirmed_edge_ids: action === 'verify' ? [...confirmed].sort() : [],
          restriction_kind: kind,
          reason: reason.trim(),
        }
        onSaved(await api.reviewReport(report.id, body, requestKey(keys, body)))
      }
    } catch (problem) {
      setError(
        problem instanceof Error ? problem.message : 'Review could not be saved. Please try again.',
      )
    } finally {
      setPending(false)
    }
  }
  return (
    <div className="report-review-editor">
      <ReportCard report={report} />
      <p className="helper">
        Opened at report revision {report.row_version}. Close and reopen this review to reload a
        changed report.
      </p>
      {report.status === 'pending_review' && (
        <fieldset disabled={pending} className="review-pathways">
          <legend>Confirm affected pathways</legend>
          <p>
            These choices become real restrictions when you verify the concern. Confirm the mapping
            from the report and evidence.
          </p>
          <label htmlFor="review-path-search">Find a pathway</label>
          <input
            id="review-path-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Ramp, steps or distance"
          />
          <div className="review-path-list">
            {candidates.slice(0, 100).map((edge) => (
              <label key={edge.id}>
                <input
                  type="checkbox"
                  checked={confirmed.includes(edge.id)}
                  onChange={(event) =>
                    setConfirmed((current) =>
                      event.target.checked
                        ? [...current, edge.id]
                        : current.filter((id) => id !== edge.id),
                    )
                  }
                />
                <span>
                  {pathwayLabel(edge)}
                  <small>
                    {edge.verification.replaceAll('_', ' ')} ·{' '}
                    {edge.effective_availability ?? edge.availability}
                  </small>
                </span>
              </label>
            ))}
          </div>
          {candidates.length > 100 && (
            <p className="helper">Showing the first 100 matching pathways. Refine the search.</p>
          )}
          <Button
            type="button"
            variant="ghost"
            size="small"
            disabled={pending}
            onClick={() => setConfirmed([])}
          >
            Clear pathway selection
          </Button>
          <Badge>
            {confirmed.length} confirmed pathway{confirmed.length === 1 ? '' : 's'}
          </Badge>
          <div className="field">
            <label htmlFor="review-restriction">Restriction</label>
            <select
              id="review-restriction"
              value={kind}
              onChange={(event) => setKind(event.target.value as typeof kind)}
            >
              <option value="temporarily_blocked">Temporarily blocked</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </fieldset>
      )}
      <div className="field">
        <label htmlFor="review-reason">
          {report.status === 'verified' ? 'Resolution reason' : 'Review reason'}
        </label>
        <textarea
          id="review-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          minLength={3}
          maxLength={500}
          rows={3}
          disabled={pending}
        />
        <small>This explanation is recorded in the report history and audit.</small>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="review-actions">
        {report.status === 'pending_review' ? (
          <>
            <Button
              busy={pending}
              disabled={reason.trim().length < 3 || !confirmed.length}
              onClick={() => void decide('verify')}
            >
              Verify concern
            </Button>
            <Button
              variant="secondary"
              busy={pending}
              disabled={reason.trim().length < 3}
              onClick={() => void decide('reject')}
            >
              Reject concern
            </Button>
          </>
        ) : report.status === 'verified' ? (
          <Button
            busy={pending}
            disabled={reason.trim().length < 3}
            onClick={() => void decide('resolve')}
          >
            Resolve concern
          </Button>
        ) : (
          <p>This report is closed to further review.</p>
        )}
      </div>
    </div>
  )
}
