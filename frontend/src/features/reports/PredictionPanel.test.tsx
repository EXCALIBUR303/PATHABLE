import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { SessionContext } from '../../app/session-context'
import { api, ApiError } from '../../services/api'
import type { Prediction, Report, Session } from '../../services/api'
import { PredictionPanel } from './PredictionPanel'

const report = { id: 'report-one', campus_id: 'campus', evidence: [] } as unknown as Report
const prediction = {
  id: 'prediction-one',
  job_id: 'job',
  report_id: report.id,
  evidence_id: 'image',
  model_version_id: 'model',
  model_name: 'Explicit test fixture',
  class_name: 'stairs',
  score: 0.8,
  box_xyxy: null,
  status: 'proposed',
  reviewer_id: null,
  reviewed_at: null,
  review_reason: null,
  row_version: 2,
  created_at: '2026-10-13T00:00:00Z',
  abstained: false,
  test_fixture: true,
} satisfies Prediction

function mount(admin = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const session = { user: { id: 'owner', role: admin ? 'admin' : 'user' } } as Session
  return render(
    <QueryClientProvider client={client}>
      <SessionContext.Provider
        value={{ session, loading: false, error: null, refresh: async () => undefined }}
      >
        <PredictionPanel report={report} />
      </SessionContext.Provider>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.restoreAllMocks())

test('unavailable ML is explicit and cannot send inference requests', async () => {
  vi.spyOn(api, 'mlStatus').mockResolvedValue({
    available: false,
    reason: 'DISABLED',
    model_name: null,
    model_version_id: null,
  })
  vi.spyOn(api, 'predictions').mockResolvedValue([])
  const invoke = vi.spyOn(api, 'requestInference')
  mount()
  await userEvent.click(screen.getByText('Image analysis'))
  expect(await screen.findByText(/Image analysis is currently unavailable/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Analyze image' })).not.toBeInTheDocument()
  expect(invoke).not.toHaveBeenCalled()
})

test('normal owner sees scores with caveats and cannot review annotations', async () => {
  vi.spyOn(api, 'mlStatus').mockResolvedValue({
    available: false,
    reason: 'DISABLED',
    model_name: null,
    model_version_id: null,
  })
  vi.spyOn(api, 'predictions').mockResolvedValue([prediction])
  mount()
  await userEvent.click(screen.getByText('Image analysis'))
  expect(await screen.findByText('Visible stairs')).toBeVisible()
  expect(screen.getByText(/not a safety probability/)).toBeVisible()
  expect(screen.getByText(/Synthetic test fixture/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Review Visible stairs' })).not.toBeInTheDocument()
})

test('stale annotation review keeps its reason and original version', async () => {
  vi.spyOn(api, 'mlStatus').mockResolvedValue({
    available: false,
    reason: 'DISABLED',
    model_name: null,
    model_version_id: null,
  })
  vi.spyOn(api, 'predictions').mockResolvedValue([prediction])
  const invoke = vi
    .spyOn(api, 'reviewPrediction')
    .mockRejectedValue(
      new ApiError(409, 'STALE_VERSION', 'Resource changed; reload before editing'),
    )
  const route = vi.spyOn(api, 'calculateRoute')
  const verify = vi.spyOn(api, 'reviewReport')
  mount(true)
  await userEvent.click(screen.getByText('Image analysis'))
  await userEvent.click(await screen.findByRole('button', { name: 'Review Visible stairs' }))
  const field = screen.getByLabelText('Annotation review reason')
  await userEvent.type(field, 'Human annotation only')
  await userEvent.click(screen.getByRole('button', { name: 'Accept annotation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Resource changed')
  expect(field).toHaveValue('Human annotation only')
  expect(invoke).toHaveBeenCalledWith(
    prediction.id,
    { decision: 'accept', reason: 'Human annotation only', expected_version: 2 },
    expect.any(String),
  )
  expect(route).not.toHaveBeenCalled()
  expect(verify).not.toHaveBeenCalled()
})
