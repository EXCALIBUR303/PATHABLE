import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Camera, Trash2 } from 'lucide-react'
import { Badge, Button } from '../../components/ui'
import { api } from '../../services/api'
import type { Report } from '../../services/api'
import { PredictionPanel } from './PredictionPanel'
import { categoryLabel, imageError, statusLabel } from './report-ui'

export function ReportCard({ report, editable = false }: { report: Report; editable?: boolean }) {
  const client = useQueryClient()
  const imageField = useRef<HTMLInputElement>(null)
  const [selected, setSelected] = useState<{ file: File; version: number }>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const slots = report.evidence.filter((item) =>
    ['processing', 'ready'].includes(item.status),
  ).length
  const canEdit = editable && report.status === 'pending_review'
  async function refresh() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['reports'] }),
      client.invalidateQueries({ queryKey: ['report', report.id] }),
    ])
  }
  async function upload() {
    if (!selected) return
    setBusy(true)
    setError('')
    try {
      await api.uploadEvidence(report.id, selected.version, selected.file)
      setSelected(undefined)
      if (imageField.current) imageField.current.value = ''
    } catch (problem) {
      setError(
        problem instanceof Error ? problem.message : 'Image upload failed. Please try again.',
      )
    } finally {
      setBusy(false)
      await refresh()
    }
  }
  async function remove(id: string) {
    setBusy(true)
    setError('')
    try {
      await api.removeEvidence(report.id, id, report.row_version)
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Image removal failed.')
    } finally {
      setBusy(false)
      await refresh()
    }
  }
  return (
    <article className="report-card" aria-label={`Report: ${categoryLabel(report.category)}`}>
      <header>
        <h3>{categoryLabel(report.category)}</h3>
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
      </header>
      <p>{report.description}</p>
      <small>
        Submitted {new Date(report.created_at).toLocaleString()} ·{' '}
        {report.data_origin === 'synthetic_demo' ? 'Fictional campus' : 'Campus report'}
      </small>
      <div className="report-evidence-list">
        {report.evidence
          .filter((item) => item.status !== 'deleted')
          .map((item) => (
            <div key={item.id} className="report-evidence-item">
              {item.status === 'ready' ? (
                <a href={api.evidenceUrl(report.id, item.id)} target="_blank" rel="noreferrer">
                  <img
                    src={api.evidenceUrl(report.id, item.id)}
                    alt={`Supporting evidence for ${categoryLabel(report.category)}`}
                    loading="lazy"
                  />
                </a>
              ) : (
                <p className="helper">
                  {item.status === 'processing'
                    ? 'Image being checked.'
                    : 'This image was not accepted.'}
                </p>
              )}
              {canEdit && item.status !== 'processing' && (
                <Button
                  variant="ghost"
                  size="small"
                  disabled={busy}
                  onClick={() => void remove(item.id)}
                  aria-label="Remove supporting image"
                >
                  <Trash2 size={14} />
                  Remove
                </Button>
              )}
            </div>
          ))}
      </div>
      {canEdit && (
        <div className="report-add-evidence">
          <label htmlFor={`evidence-${report.id}`}>
            <Camera size={15} /> Add supporting image ({slots}/3)
          </label>
          <input
            id={`evidence-${report.id}`}
            ref={imageField}
            type="file"
            accept="image/jpeg,image/png"
            disabled={busy || slots >= 3}
            onChange={(event) => {
              const file = event.target.files?.[0]
              setError(file ? imageError(file) : '')
              setSelected(
                file && !imageError(file) ? { file, version: report.row_version } : undefined,
              )
            }}
          />
          {selected && (
            <>
              <small>{selected.file.name}</small>
              <Button variant="secondary" busy={busy} onClick={() => void upload()}>
                Upload image
              </Button>
            </>
          )}
          <small>JPEG/PNG · up to 10 MiB · private to you and administrators</small>
        </div>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error} Refresh the report before retrying if it changed.
        </p>
      )}
      <PredictionPanel report={report} />
      <details>
        <summary>Review history</summary>
        <ol className="report-history">
          {report.history.map((event) => (
            <li key={event.id}>
              <strong>{event.to_status.replaceAll('_', ' ')}</strong>
              <span>{event.note}</span>
              <small>{new Date(event.occurred_at).toLocaleString()}</small>
            </li>
          ))}
        </ol>
      </details>
      {report.status === 'verified' && (
        <p className="helper">
          Confirmed concern affects {report.confirmed_edge_ids.length} mapped physical pathway
          {report.confirmed_edge_ids.length === 1 ? '' : 's'}.
        </p>
      )}
    </article>
  )
}
