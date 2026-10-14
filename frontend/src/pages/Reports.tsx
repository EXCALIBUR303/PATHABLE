import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, MessageSquare, ShieldCheck } from 'lucide-react'
import { useCampusData } from '../hooks/queries'
import { useSession } from '../app/session-context'
import { Badge, Button, ErrorNotice, Loading } from '../components/ui'
import { api } from '../services/api'
import type { ReportCreate } from '../services/api'
import { ReportCard } from '../features/reports/ReportCard'
import { categories, imageError, requestKey } from '../features/reports/report-ui'

export default function Reports() {
  const { session } = useSession()
  return <ReportWorkspace key={session?.user?.id ?? 'guest'} owner={session?.user?.id} />
}

function ReportWorkspace({ owner }: { owner?: string }) {
  const data = useCampusData()
  const client = useQueryClient()
  const [category, setCategory] = useState<ReportCreate['category']>('blocked_ramp')
  const [placeId, setPlaceId] = useState('')
  const [infrastructureId, setInfrastructureId] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File>()
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  const [cursor, setCursor] = useState<string>()
  const imageField = useRef<HTMLInputElement>(null)
  const keys = useRef<{ body: string; key: string } | null>(null)
  const reports = useQuery({
    queryKey: ['reports', owner, data.campus?.id, cursor],
    queryFn: ({ signal }) => api.reports(data.campus!.id, cursor, signal),
    enabled: !!owner && !!data.campus,
    refetchInterval: 10_000,
  })
  const place = data.locations.data?.find((item) => item.id === placeId)
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!owner || !data.campus || !place || pending) return
    const body: ReportCreate = {
      campus_id: data.campus.id,
      category,
      description: description.trim(),
      point: place.point,
      location_id: place.id,
      infrastructure_id: infrastructureId || null,
      suggested_edge_ids: [],
    }
    setPending(true)
    setError('')
    setMessage('')
    try {
      const report = await api.submitReport(body, requestKey(keys, body))
      setMessage(
        'Report submitted for administrator review. It does not change route conditions until verified.',
      )
      setDescription('')
      setFile(undefined)
      if (imageField.current) imageField.current.value = ''
      keys.current = null
      setCursor(undefined)
      if (file) {
        try {
          await api.uploadEvidence(report.id, report.row_version, file)
        } catch (problem) {
          setError(
            `Report saved. Image was not accepted: ${problem instanceof Error ? problem.message : 'Please choose another image.'}`,
          )
        }
      }
      await client.invalidateQueries({ queryKey: ['reports'] })
      await client.invalidateQueries({ queryKey: ['admin-reports'] })
      await client.invalidateQueries({ queryKey: ['analytics', data.campus.id] })
    } catch (problem) {
      setError(
        problem instanceof Error
          ? problem.message
          : 'Report submission failed. You can retry with the same details.',
      )
    } finally {
      setPending(false)
    }
  }
  return (
    <section className="page-container reporting-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">A better campus, together</div>
          <h1>
            Small observations.
            <br />
            Meaningful change.
          </h1>
          <p className="muted">Share a mapped concern for human review.</p>
        </div>
        <Badge tone="good">Community reports</Badge>
      </div>
      {data.error ? (
        <ErrorNotice error={data.error} retry={() => void data.refresh()} />
      ) : data.loading ? (
        <Loading />
      ) : (
        <div className="reporting-layout">
          <section className="report-form-panel">
            <h2>
              <MessageSquare size={22} /> Share a concern
            </h2>
            {!owner && (
              <div className="notice notice-soft">
                <p>
                  <strong>Sign in to submit a concern.</strong> Reports and supporting images are
                  private to you and campus administrators.
                </p>
                <Button asChild variant="secondary">
                  <Link to="/login?returnTo=/reports">Sign in to report</Link>
                </Button>
              </div>
            )}
            <form onSubmit={(event) => void submit(event)}>
              <fieldset disabled={pending} className="report-fields">
                <div className="field">
                  <label htmlFor="report-place">Where is the concern?</label>
                  <select
                    id="report-place"
                    value={placeId}
                    required
                    onChange={(event) => setPlaceId(event.target.value)}
                  >
                    <option value="">Choose a mapped place</option>
                    {data.locations.data?.map((location) => (
                      <option key={location.id} value={location.id}>
                        {location.name}
                      </option>
                    ))}
                  </select>
                  <small>
                    The report uses this place's mapped point. Administrators confirm affected
                    pathways.
                  </small>
                </div>
                <div className="field">
                  <label htmlFor="report-infrastructure">Related infrastructure (optional)</label>
                  <select
                    id="report-infrastructure"
                    value={infrastructureId}
                    onChange={(event) => setInfrastructureId(event.target.value)}
                  >
                    <option value="">No specific infrastructure selected</option>
                    {data.infrastructure.data?.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="report-category">What did you notice?</label>
                  <select
                    id="report-category"
                    value={category}
                    onChange={(event) =>
                      setCategory(event.target.value as ReportCreate['category'])
                    }
                  >
                    {categories.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="report-description">Tell us a little more</label>
                  <textarea
                    id="report-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    minLength={10}
                    maxLength={2000}
                    required
                    rows={5}
                    placeholder="Describe the concern and where someone might find it."
                  />
                  <small>{description.length}/2000 characters</small>
                </div>
                <div className="field">
                  <label htmlFor="report-evidence">Supporting image (optional)</label>
                  <input
                    id="report-evidence"
                    ref={imageField}
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={(event) => {
                      const image = event.target.files?.[0]
                      setError(image ? imageError(image) : '')
                      setFile(image && !imageError(image) ? image : undefined)
                    }}
                  />
                  <small>JPEG or PNG · up to 10 MiB · private upload after submission</small>
                  {file && <p className="helper">{file.name}</p>}
                </div>
              </fieldset>
              <Button
                type="submit"
                busy={pending}
                disabled={!owner || !place || description.trim().length < 10}
                className="full-width"
              >
                Submit concern <ArrowRight size={17} />
              </Button>
            </form>
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            {message && (
              <p role="status" className="success-text">
                {message}
              </p>
            )}
          </section>
          <aside className="reporting-aside">
            <span className="context-icon">
              <ShieldCheck size={27} />
            </span>
            <h2>
              Human review.
              <br />
              Clear information.
            </h2>
            <p>
              Administrators confirm a concern and its affected pathways before routes change.
              Resolving a report releases its own restrictions.
            </p>
            <p>
              Images help review. Avoid including people, personal details or sensitive information.
            </p>
            <Link className="text-link" to="/navigate">
              Explore current infrastructure <ArrowRight size={16} />
            </Link>
            <small>All campus records in this demonstration are fictional.</small>
          </aside>
        </div>
      )}
      {owner && (
        <section className="my-reports" aria-label="My reports">
          <div className="section-title">
            <h2>My reports</h2>
            <Button variant="secondary" size="small" onClick={() => void reports.refetch()}>
              Refresh reports
            </Button>
          </div>
          {reports.isPending ? (
            <Loading label="Loading your reports" />
          ) : reports.error ? (
            <ErrorNotice error={reports.error} retry={() => void reports.refetch()} />
          ) : reports.data?.items.length ? (
            <div className="report-card-list">
              {reports.data.items.map((report) => (
                <ReportCard key={report.id} report={report} editable />
              ))}
            </div>
          ) : (
            <p className="muted">You have not submitted a concern in this campus yet.</p>
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
        </section>
      )}
    </section>
  )
}
