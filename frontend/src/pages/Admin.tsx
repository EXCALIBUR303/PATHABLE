import { useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Check, ClipboardList, Info, Layers, Pencil, RefreshCw, ShieldCheck } from 'lucide-react'
import { useCampusData } from '../hooks/queries'
import type { Infrastructure } from '../services/api'
import { graphEdges } from '../features/navigation/map-data'
import { InfrastructureEditor } from '../features/admin/InfrastructureEditor'
import { ReportsAdmin } from '../features/admin/ReportsAdmin'
import { AnalyticsPanel } from '../features/admin/AnalyticsPanel'
import { Badge, Button, Dialog, ErrorNotice, Loading } from '../components/ui'

export default function Admin() {
  const data = useCampusData()
  const [editing, setEditing] = useState<Infrastructure>()
  const [message, setMessage] = useState('')
  const trigger = useRef<HTMLButtonElement | null>(null)
  const edges = graphEdges(data.graph.data)
  const chart = [
    { name: 'Verified', count: edges.filter((edge) => edge.verification === 'verified').length },
    {
      name: 'Unverified',
      count: edges.filter((edge) => edge.verification === 'unverified').length,
    },
    {
      name: 'Needs review',
      count: edges.filter((edge) => edge.verification === 'needs_review').length,
    },
  ]
  function close() {
    setEditing(undefined)
    queueMicrotask(() => trigger.current?.focus())
  }
  function refresh() {
    void data.refresh()
  }
  return (
    <section className="page-container admin-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Care for the campus</div>
          <h1>
            Clear records.
            <br />
            Better decisions.
          </h1>
          <p className="muted">
            Manage infrastructure observations in the fictional campus dataset.
          </p>
        </div>
        <Button variant="secondary" onClick={refresh}>
          <RefreshCw size={16} />
          Refresh records
        </Button>
      </div>
      {data.error ? (
        <ErrorNotice error={data.error} retry={refresh} />
      ) : data.loading ? (
        <Loading />
      ) : (
        <>
          <div className="admin-metrics">
            <article>
              <span>
                <Layers size={20} />
              </span>
              <strong>{edges.length}</strong>
              <p>Mapped physical pathways</p>
            </article>
            <article>
              <span>
                <ShieldCheck size={20} />
              </span>
              <strong>{chart[0]?.count ?? 0}</strong>
              <p>Verified pathway observations</p>
            </article>
            <article>
              <span>
                <Info size={20} />
              </span>
              <strong>{edges.filter((edge) => edge.accessibility === 'unknown').length}</strong>
              <p>Unknown accessibility labels</p>
            </article>
            <article>
              <span>
                <ClipboardList size={20} />
              </span>
              <strong>{data.infrastructure.data?.length ?? 0}</strong>
              <p>Infrastructure records</p>
            </article>
          </div>
          <div className="admin-main-grid">
            <section className="infrastructure-panel">
              <div className="section-title">
                <h2>Infrastructure records</h2>
                <Badge tone="good">Fictional campus</Badge>
              </div>
              <div className="table-scroll">
                <table>
                  <caption className="sr-only">
                    Infrastructure records and available administrator actions
                  </caption>
                  <thead>
                    <tr>
                      <th>Infrastructure</th>
                      <th>Availability</th>
                      <th>Observation</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.infrastructure.data?.map((item) => (
                      <tr key={item.id}>
                        <th>
                          <strong>{item.name.replace('Demo ', '')}</strong>
                          <small>
                            {item.kind} · {item.edge_ids.length} mapped path
                          </small>
                        </th>
                        <td>
                          <Badge tone={item.availability === 'open' ? 'good' : 'danger'}>
                            {item.availability.replaceAll('_', ' ')}
                          </Badge>
                        </td>
                        <td>{item.verification.replaceAll('_', ' ')}</td>
                        <td>
                          <Button
                            variant="ghost"
                            size="small"
                            aria-label={`Edit ${item.name}`}
                            onClick={(event) => {
                              trigger.current = event.currentTarget
                              setEditing(item)
                            }}
                          >
                            <Pencil size={15} />
                            Edit
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {message && (
                <p className="success-text" role="status">
                  <Check size={16} />
                  {message}
                </p>
              )}
            </section>
            <section className="inventory-chart">
              <h2>Observation coverage</h2>
              <p className="muted">Counts of active physical pathways, by observation status.</p>
              <div className="chart-container" aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    accessibilityLayer={false}
                    data={chart}
                    margin={{ top: 12, right: 10, left: -22, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#DCE5E0" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: '#4C6360' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 11, fill: '#4C6360' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip cursor={{ fill: '#EEF3EF' }} />
                    <Bar dataKey="count" fill="#0B625A" radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <ul className="chart-alternative" aria-label="Observation coverage counts">
                {chart.map((item) => (
                  <li key={item.name}>
                    <span>{item.name}</span>
                    <strong>{item.count}</strong>
                  </li>
                ))}
              </ul>
              <small>Observation coverage is not an accessibility or safety guarantee.</small>
            </section>
          </div>
          {data.campus && (
            <>
              <ReportsAdmin
                campusId={data.campus.id}
                edges={edges}
                infrastructure={data.infrastructure.data ?? []}
              />
              <AnalyticsPanel campusId={data.campus.id} />
            </>
          )}
        </>
      )}
      <Dialog
        title={`Edit ${editing?.name ?? 'infrastructure'}`}
        description="Changes require a reason and use the version you opened. Conflicting updates are rejected."
        open={!!editing}
        onOpenChange={(open) => {
          if (!open) close()
        }}
      >
        {editing && (
          <InfrastructureEditor
            key={`${editing.id}:${editing.row_version}`}
            item={editing}
            onSaved={() => {
              setMessage('Infrastructure updated. The map data has been refreshed.')
              close()
            }}
          />
        )}
      </Dialog>
    </section>
  )
}
