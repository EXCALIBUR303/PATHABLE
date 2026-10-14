import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../services/api'
import type { RouteRequest, RouteResult } from '../../services/api'
import type { LiveState } from '../events/useCampusEvents'

export const ROUTE_POLL_INTERVAL = 10_000

type Calculation = {
  key: string
  generation?: number
  result?: RouteResult
  deadline?: number
  staleReason?: string
  pending: boolean
  active?: boolean
  version?: string
  connectionEpoch?: number
  needsConfirmation?: boolean
  affected?: boolean
  error?: Error
}

export function useRouteCalculation(
  request: RouteRequest | null,
  knownGraphVersion?: string,
  live?: LiveState,
  selection?: { result?: RouteResult; index: number },
) {
  const key = request ? JSON.stringify(request) : ''
  const queryClient = useQueryClient()
  const generation = useRef(0)
  const flight = useRef<AbortController | null>(null)
  const [state, setState] = useState<Calculation>({ key, pending: false })
  // Retire the previous calculation on input changes, including A → B → A.
  // Adjusting derived state during render prevents one frame of an obsolete result.
  if (state.key !== key) setState({ key, pending: false })
  const current = state.key === key ? state : undefined
  const result = current?.result
  const observedVersion = [knownGraphVersion, live?.observedVersion]
    .filter((value): value is string => !!value)
    .reduce<string | undefined>(
      (highest, value) => (!highest || BigInt(value) > BigInt(highest) ? value : highest),
      undefined,
    )
  const selected =
    result?.status === 'found'
      ? ([result.primary, ...result.alternatives][
          selection?.result === result ? selection.index : 0
        ] ?? result.primary)
      : undefined
  const affected =
    !!current?.affected ||
    !!(
      result &&
      live?.lastChange &&
      BigInt(live.lastChange.graph_version) > BigInt(result.graph_version) &&
      selected?.arcs.some((arc) => live.lastChange!.changed_edge_ids.includes(arc.edge_id))
    )
  const newerGraph =
    !!current?.active &&
    !!current.version &&
    !!observedVersion &&
    BigInt(observedVersion) > BigInt(current.version)
  const newerConnection =
    !!current?.active &&
    !!live &&
    live.connectionEpoch > (current.connectionEpoch ?? live.connectionEpoch)
  const staleReason =
    current?.staleReason ??
    (newerGraph
      ? 'The campus map has changed.'
      : result && live?.disconnectedReason
        ? live.disconnectedReason
        : newerConnection
          ? 'Live updates reconnected. Campus conditions are being rechecked.'
          : undefined)

  useEffect(
    () => () => {
      generation.current++
      flight.current?.abort()
    },
    [key],
  )

  useEffect(() => {
    if (!result || !current || staleReason) return
    const calculation = current
    const controller = new AbortController()
    let checking = false
    function invalidate(reason: string) {
      setState((value) =>
        value.generation === calculation.generation && value.key === key
          ? { ...value, staleReason: reason }
          : value,
      )
    }
    async function checkVersion() {
      if (checking || document.visibilityState === 'hidden') return
      checking = true
      try {
        const version = await api.graphVersion(result!.campus_id, controller.signal)
        if (controller.signal.aborted) return
        if (
          version.graph_version !== result!.graph_version ||
          version.policy_version !== result!.policy_version ||
          version.cost_model_version !== result!.cost_model_version
        ) {
          invalidate('The campus map has changed.')
          void queryClient.invalidateQueries({ queryKey: ['graph', result!.campus_id] })
          void queryClient.invalidateQueries({ queryKey: ['infrastructure', result!.campus_id] })
        } else if (
          version.valid_until &&
          Date.parse(version.valid_until) <= Date.parse(version.validated_at)
        ) {
          invalidate('An observation used by this result has expired.')
        }
      } catch {
        if (!controller.signal.aborted)
          invalidate('We could not confirm the latest campus conditions.')
      } finally {
        checking = false
      }
    }
    const interval = window.setInterval(() => void checkVersion(), ROUTE_POLL_INTERVAL)
    const onVisibility = () => {
      if (document.visibilityState === 'visible') void checkVersion()
    }
    const onOffline = () =>
      invalidate('Your connection was interrupted. Campus conditions could not be checked.')
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('offline', onOffline)
    window.addEventListener('focus', onVisibility)
    let timeout: number | undefined
    function scheduleExpiry() {
      if (calculation.deadline === undefined) return
      const remaining = calculation.deadline - performance.now()
      if (remaining <= 0) invalidate('An observation used by this result has expired.')
      else timeout = window.setTimeout(scheduleExpiry, Math.min(remaining, 2_147_000_000))
    }
    scheduleExpiry()
    void checkVersion()
    return () => {
      controller.abort()
      window.clearInterval(interval)
      window.clearTimeout(timeout)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('offline', onOffline)
      window.removeEventListener('focus', onVisibility)
    }
  }, [current, result, staleReason, key, queryClient])

  const calculate = useCallback(
    async (automatic = false) => {
      if (!key) return
      const request = JSON.parse(key) as RouteRequest
      flight.current?.abort()
      const controller = new AbortController()
      flight.current = controller
      const token = ++generation.current
      const started = performance.now()
      setState({
        key,
        generation: token,
        pending: true,
        active: true,
        version: observedVersion,
        connectionEpoch: live?.connectionEpoch,
        affected: automatic && affected,
      })
      try {
        const response = await api.calculateRoute(request, controller.signal)
        if (!controller.signal.aborted && token === generation.current) {
          // Compare two server times, then use a monotonic browser clock. Starting at
          // request dispatch conservatively accounts for computation/network time.
          const lifetime = response.valid_until
            ? Date.parse(response.valid_until) - Date.parse(response.validated_at)
            : undefined
          const deadline = lifetime === undefined ? undefined : started + Math.max(0, lifetime)
          setState({
            key,
            generation: token,
            result: response,
            active: true,
            version: response.graph_version,
            connectionEpoch: live?.connectionEpoch,
            deadline,
            pending: false,
            needsConfirmation: automatic && response.status === 'found',
            affected: automatic && affected,
            ...(deadline !== undefined && deadline <= performance.now()
              ? { staleReason: 'An observation used by this result has expired.' }
              : {}),
          })
          void queryClient.invalidateQueries({ queryKey: ['graph', request.campus_id] })
          void queryClient.invalidateQueries({ queryKey: ['infrastructure', request.campus_id] })
        }
      } catch (error) {
        if (!controller.signal.aborted && token === generation.current)
          setState({
            key,
            generation: token,
            pending: false,
            active: true,
            version: observedVersion,
            connectionEpoch: live?.connectionEpoch,
            error:
              error instanceof Error
                ? error
                : new Error('Route calculation failed. Please try again.'),
          })
      }
    },
    [key, queryClient, observedVersion, live?.connectionEpoch, affected],
  )
  const autoAttempt = useRef('')
  useEffect(() => {
    if (
      !live ||
      live.status !== 'connected' ||
      live.disconnectedReason ||
      !current?.active ||
      !staleReason ||
      (current.pending && !newerGraph && !newerConnection)
    )
      return
    const stamp = `${key}:${observedVersion}:${live.connectionEpoch}:${staleReason.includes('expired') ? result?.valid_until : 'graph'}`
    if (autoAttempt.current === stamp) return
    const timer = window.setTimeout(() => {
      autoAttempt.current = stamp
      void calculate(true)
    }, 250)
    return () => window.clearTimeout(timer)
  }, [
    live,
    key,
    observedVersion,
    result,
    staleReason,
    current?.pending,
    current?.active,
    newerGraph,
    newerConnection,
    calculate,
  ])
  function confirm() {
    if (staleReason) return
    setState((value) =>
      value.key === key ? { ...value, needsConfirmation: false, affected: false } : value,
    )
  }
  return {
    result,
    staleReason,
    pending: current?.pending ?? false,
    error: current?.error,
    calculate,
    needsConfirmation: current?.needsConfirmation ?? false,
    confirm,
    affected,
  }
}
