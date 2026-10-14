import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSession } from '../../app/session-context'
import { Badge, Button } from '../../components/ui'
import { api } from '../../services/api'
import type { Prediction, Report } from '../../services/api'
import { requestKey } from './report-ui'

const labels: Record<string, string> = {
  stairs: 'Visible stairs',
  pathway_obstruction: 'Pathway obstruction',
  damaged_pavement: 'Damaged pavement',
  ramp_obstruction: 'Ramp obstruction',
  no_visible_target: 'No target observation',
}

function AnnotationReview({ prediction, saved }: { prediction: Prediction; saved: () => void }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const keys = useRef<{ body: string; key: string } | null>(null)
  async function review(decision: 'accept' | 'reject') {
    setBusy(true)
    setError('')
    const body = { decision, expected_version: prediction.row_version, reason: reason.trim() }
    try {
      await api.reviewPrediction(prediction.id, body, requestKey(keys, body))
      saved()
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Annotation review failed.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="annotation-review">
      <p>
        Reviewing {labels[prediction.class_name]} at revision {prediction.row_version}.
      </p>
      <label htmlFor={`prediction-reason-${prediction.id}`}>Annotation review reason</label>
      <textarea
        id={`prediction-reason-${prediction.id}`}
        value={reason}
        maxLength={2000}
        onChange={(event) => setReason(event.target.value)}
        disabled={busy}
      />
      <div className="button-row">
        <Button
          busy={busy}
          disabled={reason.trim().length < 5}
          onClick={() => void review('accept')}
        >
          Accept annotation
        </Button>
        <Button
          variant="secondary"
          disabled={busy || reason.trim().length < 5}
          onClick={() => void review('reject')}
        >
          Reject annotation
        </Button>
      </div>
      {error && (
        <p role="alert" className="form-error">
          {error} Close and reopen this annotation to reload its version.
        </p>
      )}
      <p className="helper">
        Accepting an annotation does not verify this report or change routes.
      </p>
    </div>
  )
}

export function PredictionPanel({ report }: { report: Report }) {
  const { session } = useSession()
  const client = useQueryClient()
  const identity = session?.user?.id
  const admin = session?.user?.role === 'admin'
  const [evidenceId, setEvidenceId] = useState('')
  const [jobId, setJobId] = useState<string>()
  const [selected, setSelected] = useState<Prediction>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const key = useRef<{ body: string; key: string } | null>(null)
  const status = useQuery({
    queryKey: ['ml-status'],
    queryFn: ({ signal }) => api.mlStatus(signal),
    staleTime: 30_000,
  })
  const predictions = useQuery({
    queryKey: ['predictions', identity, report.id],
    enabled: !!identity,
    queryFn: ({ signal }) => api.predictions(report.id, signal),
    refetchInterval: 10_000,
  })
  const job = useQuery({
    queryKey: ['inference-jobs', identity, report.id, jobId],
    enabled: !!identity && !!jobId,
    queryFn: ({ signal }) => api.inferenceJob(report.id, jobId!, signal),
    refetchInterval: (query) =>
      ['queued', 'running'].includes(query.state.data?.status ?? '') ? 1000 : false,
  })
  useEffect(() => {
    if (job.data?.status === 'succeeded')
      void client.invalidateQueries({ queryKey: ['predictions', identity, report.id] })
  }, [job.data?.status, client, identity, report.id])
  const ready = report.evidence.filter((item) => item.status === 'ready')
  async function analyze() {
    if (!evidenceId) return
    setBusy(true)
    setError('')
    try {
      const body = { evidence_id: evidenceId }
      const value = await api.requestInference(report.id, body, requestKey(key, body))
      setJobId(value.id)
      await client.invalidateQueries({ queryKey: ['predictions', identity, report.id] })
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Image analysis failed.')
    } finally {
      setBusy(false)
    }
  }
  function saved() {
    setSelected(undefined)
    setMessage('Annotation review saved. Route conditions have not changed.')
    void client.invalidateQueries({ queryKey: ['predictions', identity, report.id] })
    void client.invalidateQueries({ queryKey: ['audit', report.campus_id] })
  }
  return (
    <details className="prediction-panel">
      <summary>Image analysis</summary>
      <p className="helper">
        Image observations assist human review. They do not measure accessibility or guarantee route
        safety.
      </p>
      {status.isPending ? (
        <p>Checking image analysis availability…</p>
      ) : status.error ? (
        <p role="status">Image analysis could not be checked. Manual review remains available.</p>
      ) : !status.data?.available ? (
        <p role="status">
          Image analysis is currently unavailable. Manual reporting and review remain available.
        </p>
      ) : (
        <div>
          <label htmlFor={`analysis-image-${report.id}`}>Image to analyze</label>
          <select
            id={`analysis-image-${report.id}`}
            value={evidenceId}
            onChange={(event) => setEvidenceId(event.target.value)}
            disabled={busy}
          >
            <option value="">Choose a normalized image</option>
            {ready.map((image, index) => (
              <option key={image.id} value={image.id}>
                Supporting image {index + 1}
              </option>
            ))}
          </select>
          <Button disabled={!evidenceId || busy} busy={busy} onClick={() => void analyze()}>
            Analyze image
          </Button>
          {!ready.length && <p>Add a valid supporting image before requesting analysis.</p>}
          <p className="helper">
            Model: {status.data.model_name}. Analysis may wait for the worker.
          </p>
        </div>
      )}
      {job.data && (
        <p role="status">
          Analysis {job.data.status.replaceAll('_', ' ')}
          {job.data.abstained ? ': uncertain observation' : ''}.
          {['failed', 'unavailable'].includes(job.data.status) &&
            ' Manual review remains available.'}
        </p>
      )}
      {job.error && <p role="alert">Analysis status could not be loaded.</p>}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {predictions.error && <p role="alert">Image observations could not be loaded.</p>}
      {predictions.data?.length === 0 && <p>No image observations have been recorded.</p>}
      <ul className="prediction-list">
        {predictions.data?.map((prediction) => (
          <li key={prediction.id}>
            <strong>{labels[prediction.class_name] ?? prediction.class_name}</strong>
            <Badge tone={prediction.status === 'accepted' ? 'good' : 'warning'}>
              {prediction.status}
            </Badge>
            <p>
              Model score {(prediction.score * 100).toFixed(1)}% · {prediction.model_name}
            </p>
            <small>
              {prediction.abstained
                ? 'Uncertain; the model abstained.'
                : 'Uncalibrated model score, not a safety probability.'}
            </small>
            {prediction.test_fixture && (
              <p className="form-error">Synthetic test fixture — not a product prediction.</p>
            )}
            <a
              href={api.evidenceUrl(report.id, prediction.evidence_id)}
              target="_blank"
              rel="noreferrer"
            >
              View private source image
            </a>
            {prediction.review_reason && <p>Review: {prediction.review_reason}</p>}
            {admin && prediction.status === 'proposed' && (
              <Button variant="secondary" onClick={() => setSelected({ ...prediction })}>
                Review {labels[prediction.class_name]}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {selected && (
        <div>
          <AnnotationReview key={selected.id} prediction={selected} saved={saved} />
          <Button variant="secondary" onClick={() => setSelected(undefined)}>
            Close annotation review
          </Button>
        </div>
      )}
    </details>
  )
}
