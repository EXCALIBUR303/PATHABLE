import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../services/api'
import { Button, ErrorNotice, Loading } from '../../components/ui'
import { categoryLabel } from '../reports/report-ui'

const day = (offset: number) => new Date(Date.now() + offset * 86400_000).toISOString().slice(0, 10)
const shortCategories: Record<string, string> = {
  blocked_ramp: 'Ramp',
  inaccessible_entrance: 'Entrance',
  damaged_pathway: 'Pathway',
  elevator_unavailable: 'Elevator',
  temporary_obstacle: 'Temporary',
  other_accessibility_concern: 'Other',
}

export function AnalyticsPanel({ campusId }: { campusId: string }) {
  const [from, setFrom] = useState(() => day(-30))
  const [until, setUntil] = useState(() => day(1))
  const [cursor, setCursor] = useState<string>()
  const duration = Date.parse(`${until}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)
  const valid = Number.isFinite(duration) && duration > 0 && duration <= 366 * 86400_000
  const analytics = useQuery({
    queryKey: ['analytics', campusId, from, until],
    refetchInterval: 30_000,
    queryFn: ({ signal }) =>
      api.analytics(campusId, `${from}T00:00:00Z`, `${until}T00:00:00Z`, signal),
    enabled: valid,
  })
  const audit = useQuery({
    queryKey: ['audit', campusId, cursor],
    refetchInterval: 10_000,
    queryFn: ({ signal }) => api.audit(campusId, cursor, signal),
  })
  const data = analytics.data
  const chart =
    data?.category_distribution.map((entry) => ({
      ...entry,
      name: shortCategories[entry.category] ?? entry.category,
      label: categoryLabel(entry.category),
    })) ?? []
  return (
    <section className="analytics-panel" aria-label="Campus analytics">
      <div className="section-title">
        <h2>Campus analytics</h2>
        <Button variant="secondary" size="small" onClick={() => void analytics.refetch()}>
          Refresh analytics
        </Button>
      </div>
      <p className="muted">
        Current records and report activity in the fictional campus. Mapping coverage refers to the
        mapped network.
      </p>
      <div className="analytics-window">
        <div className="field">
          <label htmlFor="analytics-from">From (inclusive, UTC)</label>
          <input
            type="date"
            id="analytics-from"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="analytics-until">Until (exclusive, UTC)</label>
          <input
            type="date"
            id="analytics-until"
            value={until}
            onChange={(event) => setUntil(event.target.value)}
          />
        </div>
      </div>
      {!valid ? (
        <p className="form-error" role="alert">
          Choose an increasing date range of at most 366 days.
        </p>
      ) : analytics.isPending ? (
        <Loading label="Loading analytics" />
      ) : analytics.error ? (
        <ErrorNotice error={analytics.error} retry={() => void analytics.refetch()} />
      ) : (
        data && (
          <>
            <div className="analytics-metrics">
              <article>
                <strong>{data.active_verified_obstacles}</strong>
                <span>Active verified concerns</span>
              </article>
              <article>
                <strong>{data.pending_reports}</strong>
                <span>Awaiting review</span>
              </article>
              <article>
                <strong>{data.verified_accessible_pathways}</strong>
                <span>Current accessible labels</span>
              </article>
              <article>
                <strong>
                  {data.accessibility_mapping_coverage === null
                    ? '—'
                    : `${(data.accessibility_mapping_coverage * 100).toFixed(1)}%`}
                </strong>
                <span>Mapped observation coverage</span>
              </article>
            </div>
            <p className="helper">
              Current as of {new Date(data.as_of).toLocaleString()}. Coverage:{' '}
              {data.mapping_known_current_length_m.toFixed(1)} m with a known, current accessibility
              label / {data.mapping_total_length_m.toFixed(1)} m mapped. Labels and coverage do not
              guarantee individual suitability.
            </p>
            <div className="analytics-flow-metrics">
              <p>
                <strong>{data.submitted_report_count}</strong> reports submitted in the selected
                window
              </p>
              <p>
                <strong>{data.resolved_report_count}</strong> reports resolved in the selected
                window
              </p>
              <p>
                Mean time to resolution:{' '}
                <strong>
                  {data.average_resolution_seconds === null
                    ? 'No resolved reports'
                    : `${data.average_resolution_seconds.toFixed(1)} seconds`}
                </strong>{' '}
                ({data.resolved_report_count} resolved reports)
              </p>
            </div>
            <div className="analytics-charts">
              <section>
                <h3>Submitted concerns by category</h3>
                {chart.length ? (
                  <div className="chart-container" aria-hidden="true">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        accessibilityLayer={false}
                        data={chart}
                        margin={{ left: -20, right: 10, top: 15, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#0B625A" radius={[5, 5, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p>No submissions in this window.</p>
                )}
                <table>
                  <caption className="sr-only">Submitted concerns by category</caption>
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Reports</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chart.map((entry) => (
                      <tr key={entry.category}>
                        <th>{entry.label}</th>
                        <td>{entry.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <section>
                <h3>Resolution trend (UTC)</h3>
                {data.resolution_trend.length ? (
                  <div className="chart-container" aria-hidden="true">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        accessibilityLayer={false}
                        data={data.resolution_trend}
                        margin={{ left: -20, right: 20, top: 15, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Line dataKey="count" stroke="#285F8F" strokeWidth={3} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p>No resolutions in this window.</p>
                )}
                <table>
                  <caption className="sr-only">Resolved reports by UTC date</caption>
                  <thead>
                    <tr>
                      <th>UTC day</th>
                      <th>Resolved reports</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.resolution_trend.map((entry) => (
                      <tr key={entry.day}>
                        <th>{entry.day}</th>
                        <td>{entry.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
            <details>
              <summary>Current inventory counts</summary>
              <dl className="path-details">
                {[
                  ['Mapped physical pathways', data.active_physical_pathways],
                  ['Infrastructure records', data.mapped_infrastructure_count],
                  ['Unknown accessibility labels', data.unknown_accessibility_pathways],
                  ['Pathways needing review', data.needs_review_pathways],
                  ['Unverified pathways', data.unverified_pathways],
                ].map(([label, count]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{count}</dd>
                  </div>
                ))}
              </dl>
            </details>
          </>
        )
      )}
      <section className="audit-panel" aria-label="Administrative audit history">
        <div className="section-title">
          <h3>Administrative audit history</h3>
          <Button variant="secondary" size="small" onClick={() => void audit.refetch()}>
            Refresh audit
          </Button>
        </div>
        {audit.isPending ? (
          <Loading label="Loading audit history" />
        ) : audit.error ? (
          <ErrorNotice error={audit.error} retry={() => void audit.refetch()} />
        ) : audit.data?.items.length ? (
          <div className="table-scroll">
            <table>
              <caption className="sr-only">
                Administrative changes with reasons and resulting graph revisions
              </caption>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Reason</th>
                  <th>Recorded</th>
                  <th>Graph revision</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.items.map((entry) => (
                  <tr key={entry.id}>
                    <th>{entry.action_type.replaceAll('_', ' ')}</th>
                    <td>{entry.reason}</td>
                    <td>{new Date(entry.created_at).toLocaleString()}</td>
                    <td>{entry.graph_version ?? 'No graph change'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No administrative changes have been recorded.</p>
        )}
        <div className="report-pagination">
          {cursor && (
            <Button variant="secondary" onClick={() => setCursor(undefined)}>
              First audit page
            </Button>
          )}
          {audit.data?.next_cursor && (
            <Button variant="secondary" onClick={() => setCursor(audit.data!.next_cursor!)}>
              Next audit records
            </Button>
          )}
        </div>
      </section>
    </section>
  )
}
