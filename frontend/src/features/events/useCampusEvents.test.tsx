import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../../services/api'
import type { GraphVersion } from '../../services/api'
import { consumeGraphStream } from './stream'
import { useCampusEvents } from './useCampusEvents'

vi.mock('./stream', () => ({ consumeGraphStream: vi.fn() }))
const metadata: GraphVersion = {
  graph_version: '1',
  validated_at: '2026-10-13T00:00:00Z',
  valid_until: null,
  data_origin: 'synthetic_demo',
  policy_version: 'accessibility-v1',
  cost_model_version: 'walking-effort-v1',
}
type Flight = {
  cursor?: string
  signal: AbortSignal
  callbacks: Parameters<typeof consumeGraphStream>[3]
}
function setup() {
  const flights: Flight[] = []
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  vi.spyOn(api, 'graphVersion').mockResolvedValue(metadata)
  vi.mocked(consumeGraphStream).mockImplementation(async (_campus, cursor, signal, callbacks) => {
    flights.push({ cursor, signal, callbacks })
    await callbacks.open()
    await new Promise<void>((resolve) =>
      signal.addEventListener('abort', () => resolve(), { once: true }),
    )
  })
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  const view = renderHook(({ userId }) => useCampusEvents('campus', userId), {
    wrapper,
    initialProps: { userId: undefined as string | undefined },
  })
  return { view, flights, invalidate }
}
function update(flight: Flight, version: string) {
  flight.callbacks.event({
    type: 'graph.updated',
    id: version,
    data: {
      campus_id: 'campus',
      graph_version: version,
      changed_edge_ids: [],
      changes_truncated: false,
      reason: 'report_verified',
      occurred_at: metadata.validated_at,
    },
  })
}
afterEach(() => vi.useRealTimers())

it('ignores duplicate/older revisions, refreshes across gaps and resumes with the committed cursor', async () => {
  vi.useFakeTimers()
  const { view, flights, invalidate } = setup()
  await act(async () => {
    await Promise.resolve()
  })
  expect(view.result.current.status).toBe('connected')
  invalidate.mockClear()
  act(() => {
    update(flights[0]!, '2')
    update(flights[0]!, '2')
    update(flights[0]!, '1')
  })
  expect(view.result.current.observedVersion).toBe('2')
  const calls = invalidate.mock.calls.length
  act(() => update(flights[0]!, '5'))
  expect(view.result.current.observedVersion).toBe('5')
  expect(invalidate.mock.calls.length).toBeGreaterThan(calls)
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['graph', 'campus'] })
  vi.mocked(api.graphVersion).mockResolvedValue({ ...metadata, graph_version: '5' })
  await act(async () => {
    window.dispatchEvent(new Event('offline'))
    await Promise.resolve()
  })
  expect(view.result.current.status).toBe('disconnected')
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500)
  })
  expect(flights[1]?.cursor).toBe('5')
  expect(view.result.current.status).toBe('connected')
  expect(view.result.current.connectionEpoch).toBe(2)
})

it('counts comment heartbeats and retires the stream after 45 seconds without one', async () => {
  vi.useFakeTimers()
  const { view, flights } = setup()
  await act(async () => {
    await Promise.resolve()
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(30_000)
  })
  act(() => flights[0]!.callbacks.heartbeat())
  await act(async () => {
    await vi.advanceTimersByTimeAsync(44_000)
  })
  expect(view.result.current.status).toBe('connected')
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000)
  })
  expect(view.result.current.disconnectedReason).toMatch(/stopped responding/)
  expect(flights[0]?.signal.aborted).toBe(true)
})

it('closes the old identity stream and ignores its late callback after a session change', async () => {
  const { view, flights } = setup()
  await act(async () => {
    await Promise.resolve()
  })
  const original = flights[0]!
  view.rerender({ userId: 'new-owner' })
  await act(async () => {
    await Promise.resolve()
  })
  expect(original.signal.aborted).toBe(true)
  expect(flights[1]?.cursor).toBeUndefined()
  act(() => update(original, '99'))
  expect(view.result.current.observedVersion).toBe('1')
  view.unmount()
  expect(flights[1]?.signal.aborted).toBe(true)
})

it('reconnects after failed resume confirmation and ignores callbacks from the cancelled connection', async () => {
  vi.useFakeTimers()
  const { view, flights } = setup()
  await act(async () => {
    await Promise.resolve()
  })
  vi.mocked(api.graphVersion).mockRejectedValueOnce(new Error('Temporary metadata outage'))
  await act(async () => {
    window.dispatchEvent(new Event('focus'))
    await Promise.resolve()
  })
  expect(view.result.current.status).toBe('disconnected')
  expect(flights[0]?.signal.aborted).toBe(true)
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500)
  })
  expect(view.result.current.status).toBe('connected')
  act(() => update(flights[0]!, '99'))
  expect(view.result.current.observedVersion).toBe('1')
})

it('accepts an authoritative reset after a future cursor while retiring the old connection epoch', async () => {
  const { view, flights } = setup()
  await act(async () => {
    await Promise.resolve()
  })
  act(() => update(flights[0]!, '5'))
  const epoch = view.result.current.connectionEpoch
  act(() =>
    flights[0]!.callbacks.event({
      type: 'graph.reset',
      id: '1',
      data: {
        campus_id: 'campus',
        graph_version: '1',
        changed_edge_ids: [],
        changes_truncated: false,
        reason: 'cursor_reset',
        occurred_at: metadata.validated_at,
      },
    }),
  )
  expect(view.result.current.observedVersion).toBe('1')
  expect(view.result.current.connectionEpoch).toBe(epoch + 1)
})
