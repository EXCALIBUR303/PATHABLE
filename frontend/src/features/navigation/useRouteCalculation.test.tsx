import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../services/api'
import type { LiveState } from '../events/useCampusEvents'
import type { RouteRequest, RouteResult } from '../../services/api'
import { useRouteCalculation, ROUTE_POLL_INTERVAL } from './useRouteCalculation'

const request: RouteRequest = {
  campus_id: 'campus',
  source_id: 'source',
  destination_id: 'destination',
  accessibility_profile: {
    avoid_stairs: true,
    max_slope_pct: 8,
    min_width_m: 0.9,
    excluded_surfaces: ['uneven', 'gravel'],
    unknown_policy: 'exclude',
    travel_speed_mps: 1,
  },
  selected_algorithm: 'astar',
  alternatives_limit: 2,
}
const response: RouteResult = {
  ...request,
  status: 'no_route',
  reason: 'constraints_exclude_all_paths',
  primary: null,
  alternatives: [],
  alternatives_exhaustive: true,
  excluded_edge_counts: { stairs: 2 },
  warnings: [],
  graph_version: '1',
  policy_version: 'accessibility-v1',
  cost_model_version: 'walking-effort-v1',
  profile_fingerprint: 'fingerprint',
  algorithm: 'astar',
  validated_at: '2026-10-13T12:00:00Z',
  valid_until: null,
  data_origin: 'synthetic_demo',
  stats: { expansions: 3, searches: 1, elapsed_ms: 1, alternative_candidates: 0 },
}
function setup(value = request) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  vi.spyOn(api, 'graphVersion').mockResolvedValue(response)
  return renderHook(({ input }) => useRouteCalculation(input), {
    wrapper,
    initialProps: { input: value },
  })
}
afterEach(() => vi.useRealTimers())

describe('route response currentness', () => {
  it('retires a completed result when inputs change and does not resurrect A after A → B → A', async () => {
    vi.spyOn(api, 'calculateRoute').mockResolvedValue(response)
    const view = setup()
    await act(async () => {
      await view.result.current.calculate()
    })
    expect(view.result.current.result?.status).toBe('no_route')
    view.rerender({ input: { ...request, destination_id: 'other' } })
    expect(view.result.current.result).toBeUndefined()
    view.rerender({ input: request })
    expect(view.result.current.result).toBeUndefined()
  })

  it('aborts a previous flight and ignores a late response even if the transport ignores abort', async () => {
    let resolve!: (value: RouteResult) => void
    const calculate = vi
      .spyOn(api, 'calculateRoute')
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            resolve = done
          }),
      )
      .mockResolvedValue({ ...response, destination_id: 'other' })
    const view = setup()
    act(() => {
      void view.result.current.calculate()
    })
    const signal = calculate.mock.calls[0]?.[1]
    view.rerender({ input: { ...request, destination_id: 'other' } })
    expect(signal?.aborted).toBe(true)
    await act(async () => {
      await view.result.current.calculate()
    })
    await act(async () => {
      resolve(response)
    })
    expect(view.result.current.result?.destination_id).toBe('other')
  })

  it('uses the server lifetime and monotonic time when the device clock is years behind', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2001-01-01T00:00:00Z'))
    vi.spyOn(api, 'calculateRoute').mockResolvedValue({
      ...response,
      valid_until: '2026-10-13T12:00:01Z',
    })
    const view = setup()
    await act(async () => {
      await view.result.current.calculate()
    })
    expect(view.result.current.staleReason).toBeUndefined()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1001)
    })
    expect(view.result.current.staleReason).toMatch(/expired/)
  })

  it('invalidates after a changed graph revision or failed confirmation without issuing an automatic route retry', async () => {
    vi.useFakeTimers()
    const calculate = vi.spyOn(api, 'calculateRoute').mockResolvedValue(response)
    const view = setup()
    await act(async () => {
      await view.result.current.calculate()
    })
    vi.mocked(api.graphVersion).mockResolvedValue({ ...response, graph_version: '2' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ROUTE_POLL_INTERVAL)
    })
    expect(view.result.current.staleReason).toMatch(/map has changed/)
    expect(calculate).toHaveBeenCalledTimes(1)
    vi.mocked(api.graphVersion).mockRejectedValue(new Error('Offline'))
    await act(async () => {
      await view.result.current.calculate()
    })
    expect(view.result.current.staleReason).toMatch(/could not confirm/)
    expect(calculate).toHaveBeenCalledTimes(2)
  })

  it('keeps service errors distinct from a no-route result', async () => {
    vi.spyOn(api, 'calculateRoute').mockRejectedValue(new Error('Search budget exceeded'))
    const view = setup()
    await act(async () => {
      await view.result.current.calculate()
    })
    expect(view.result.current.error?.message).toBe('Search budget exceeded')
    expect(view.result.current.result).toBeUndefined()
    expect(view.result.current.pending).toBe(false)
  })
})

const found: RouteResult = {
  ...response,
  status: 'found',
  reason: null,
  primary: {
    node_ids: ['source', 'destination'],
    arcs: [{ edge_id: 'edge', direction: 'forward' }],
    geometry: {
      type: 'LineString',
      coordinates: [
        [0, 0],
        [0.000001, 0],
      ],
    },
    total_distance_m: 1,
    estimated_duration_s: 1,
    cost_m_equivalent: 1,
    instructions: [],
    warnings: [],
    verification: {
      summary: 'observations_current',
      verified_distance_m: 1,
      uncertain_distance_m: 0,
      earliest_expiry_at: null,
    },
  },
  alternatives: [],
}
const connected: LiveState = {
  key: 'campus:guest',
  status: 'connected' as const,
  observedVersion: '1',
  connectionEpoch: 1,
}
function setupLive() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  vi.spyOn(api, 'graphVersion').mockResolvedValue(response)
  return renderHook(({ live }) => useRouteCalculation(request, undefined, live), {
    wrapper,
    initialProps: { live: connected },
  })
}

describe('live rerouting and explicit confirmation', () => {
  it('retires immediately, debounces a version burst and requires confirmation of the fresh response', async () => {
    vi.useFakeTimers()
    const calculate = vi.spyOn(api, 'calculateRoute').mockResolvedValue(found)
    const view = setupLive()
    await act(async () => {
      await view.result.current.calculate()
    })
    calculate.mockResolvedValue({ ...found, graph_version: '3' })
    vi.mocked(api.graphVersion).mockResolvedValue({ ...response, graph_version: '3' })
    view.rerender({ live: { ...connected, observedVersion: '2' } })
    expect(view.result.current.staleReason).toMatch(/changed/)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200)
    })
    view.rerender({ live: { ...connected, observedVersion: '3' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200)
    })
    expect(calculate).toHaveBeenCalledTimes(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(51)
    })
    expect(calculate).toHaveBeenCalledTimes(2)
    expect(calculate.mock.calls[1]?.[0].accessibility_profile).toEqual(
      request.accessibility_profile,
    )
    expect(view.result.current.result?.graph_version).toBe('3')
    expect(view.result.current.needsConfirmation).toBe(true)
    act(() => view.result.current.confirm())
    expect(view.result.current.needsConfirmation).toBe(false)
  })
  it('cancels a superseded recalculation and ignores its late old revision', async () => {
    vi.useFakeTimers()
    let resolve!: (value: RouteResult) => void
    const calculate = vi
      .spyOn(api, 'calculateRoute')
      .mockResolvedValueOnce(found)
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            resolve = done
          }),
      )
      .mockResolvedValue({ ...found, graph_version: '3' })
    const view = setupLive()
    await act(async () => {
      await view.result.current.calculate()
    })
    view.rerender({ live: { ...connected, observedVersion: '2' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(251)
    })
    const signal = calculate.mock.calls[1]?.[1]
    vi.mocked(api.graphVersion).mockResolvedValue({ ...response, graph_version: '3' })
    view.rerender({ live: { ...connected, observedVersion: '3' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(251)
    })
    expect(signal?.aborted).toBe(true)
    expect(calculate).toHaveBeenCalledTimes(3)
    await act(async () => {
      resolve({ ...found, graph_version: '2' })
    })
    expect(view.result.current.result?.graph_version).toBe('3')
    expect(view.result.current.needsConfirmation).toBe(true)
  })
  it('recalculates on confirmed reconnect even when the campus revision is unchanged', async () => {
    vi.useFakeTimers()
    const calculate = vi.spyOn(api, 'calculateRoute').mockResolvedValue(found)
    const view = setupLive()
    await act(async () => {
      await view.result.current.calculate()
    })
    view.rerender({
      live: {
        ...connected,
        status: 'disconnected',
        disconnectedReason: 'Live updates disconnected.',
      },
    })
    expect(view.result.current.staleReason).toMatch(/disconnected/)
    view.rerender({ live: { ...connected, connectionEpoch: 2 } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(251)
    })
    expect(calculate).toHaveBeenCalledTimes(2)
    expect(view.result.current.needsConfirmation).toBe(true)
  })
  it('keeps an automatic no-route result honest and does not loop after a failed reroute', async () => {
    vi.useFakeTimers()
    const calculate = vi
      .spyOn(api, 'calculateRoute')
      .mockResolvedValueOnce(found)
      .mockResolvedValueOnce({ ...response, graph_version: '2' })
      .mockRejectedValue(new Error('Service unavailable'))
    const view = setupLive()
    await act(async () => {
      await view.result.current.calculate()
    })
    vi.mocked(api.graphVersion).mockResolvedValue({ ...response, graph_version: '2' })
    view.rerender({ live: { ...connected, observedVersion: '2' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(251)
    })
    expect(view.result.current.result?.status).toBe('no_route')
    expect(view.result.current.needsConfirmation).toBe(false)
    view.rerender({ live: { ...connected, observedVersion: '3' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(251)
    })
    expect(view.result.current.error?.message).toBe('Service unavailable')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000)
    })
    expect(calculate).toHaveBeenCalledTimes(3)
  })
})
