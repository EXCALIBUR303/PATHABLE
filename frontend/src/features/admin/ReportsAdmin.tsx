import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { Edge, Infrastructure, Report } from '../../services/api'
import { api } from '../../services/api'
import { Badge, Button, Dialog, ErrorNotice, Loading } from '../../components/ui'
import { categoryLabel, statusLabel } from '../reports/report-ui'
import { ReportReviewEditor } from './ReportReviewEditor'

export function ReportsAdmin({
  campusId,
  edges,
  infrastructure,
}: {
  campusId: string
  edges: Edge[]
  infrastructure: Infrastructure[]
}) {
  const client = useQueryClient()
  const [status, setStatus] = useState<Report['status'] | 'all'>('pending_review')
  const [cursor, setCursor] = useState<string>()
  const [selected, setSelected] = useState<Report>()
  const [message, setMessage] = useState('')
  const trigger = useRef<HTMLButtonElement | null>(null)
  const refreshTrigger = useRef<HTMLButtonElement | null>(null)
  const reports = useQuery({
    queryKey: ['admin-reports', campusId, status, cursor],
    refetchInterval: 10_000,
    queryFn: ({ signal }) =>
      api.adminReports(campusId, status === 'all' ? undefined : status, cursor, signal),
  })
  function close(useRefresh = false) {
    setSelected(undefined)
    queueMicrotask(() => {
      if (!useRefresh && trigger.current?.isConnected) trigger.current.focus()
      else refreshTrigger.current?.focus()
    })
  }
  function saved(report: Report) {
    setMessage(`${categoryLabel(report.category)}: ${statusLabel(report.status).toLowerCase()}.`)
    close(true)
    for (const queryKey of [
      ['admin-reports'],
      ['reports'],
      ['analytics', campusId],
      ['audit', campusId],
      ['graph', campusId],
      ['infrastructure', campusId],
    ])
      void client.invalidateQueries({ queryKey })
  }
  return (
    <section className="report-review-panel" aria-label="Report review queue">
      <div className="section-title">
        <h2>Report review</h2>
        <Button
          ref={refreshTrigger}
          variant="secondary"
          size="small"
          onClick={() => void reports.refetch()}
        >
          Refresh review queue
        </Button>
      </div>
      <div className="field report-filter">
        <label htmlFor="report-status-filter">Report status</label>
        <select
          id="report-status-filter"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as typeof status)
            setCursor(undefined)
          }}
        >
          <option value="pending_review">Awaiting review</option>
          <option value="verified">Verified concerns</option>
          <option value="resolved">Resolved</option>
          <option value="rejected">Not verified</option>
          <option value="all">All reports</option>
        </select>
      </div>
      {message && (
        <p className="success-text" role="status">
          {message}
        </p>
      )}
      {reports.isPending ? (
        <Loading label="Loading review queue" />
      ) : reports.error ? (
        <ErrorNotice error={reports.error} retry={() => void reports.refetch()} />
      ) : reports.data?.items.length ? (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Reports and administrator review actions</caption>
            <thead>
              <tr>
                <th>Concern</th>
                <th>Review state</th>
                <th>Submitted</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.data.items.map((report) => (
                <tr key={report.id}>
                  <th>
                    <strong>{categoryLabel(report.category)}</strong>
                    <small>{report.description}</small>
                  </th>
                  <td>
                    <Badge
                      tone={
                        report.status === 'verified'
                          ? 'danger'
                          : report.status === 'resolved'
                            ? 'good'
                            : 'warning'
                      }
                    >
                      {statusLabel(report.status)}
                    </Badge>
                  </td>
                  <td>{new Date(report.created_at).toLocaleString()}</td>
                  <td>
                    <Button
                      size="small"
                      variant="secondary"
                      onClick={(event) => {
                        trigger.current = event.currentTarget
                        setSelected(report)
                      }}
                    >
                      {report.status === 'verified'
                        ? 'Resolve concern'
                        : report.status === 'pending_review'
                          ? 'Review concern'
                          : 'View history'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No reports match this review status.</p>
      )}
      <div className="report-pagination">
        {cursor && (
          <Button variant="secondary" onClick={() => setCursor(undefined)}>
            First page
          </Button>
        )}
        {reports.data?.next_cursor && (
          <Button variant="secondary" onClick={() => setCursor(reports.data!.next_cursor!)}>
            Next reports
          </Button>
        )}
      </div>
      <Dialog
        title={selected?.status === 'verified' ? 'Resolve concern' : 'Review concern'}
        description="Confirm the evidence and affected pathways. Changes use the revision you opened and require a recorded reason."
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) close()
        }}
      >
        {selected && (
          <ReportReviewEditor
            key={selected.id}
            report={selected}
            edges={edges}
            infrastructure={infrastructure}
            onSaved={saved}
          />
        )}
      </Dialog>
    </section>
  )
}
