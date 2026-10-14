import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../services/api'
import { consumeGraphStream } from './stream'
import type { GraphEvent } from './stream'

export type LiveState = {
  key: string
  status: 'connecting' | 'connected' | 'disconnected'
  observedVersion?: string
  disconnectedReason?: string
  connectionEpoch: number
  lastChange?: GraphEvent
}

export function useCampusEvents(campusId?: string, userId?: string) {
  const key = `${campusId ?? ''}:${userId ?? 'guest'}`
  const client = useQueryClient()
  const [state, setState] = useState<LiveState>({ key, status: 'connecting', connectionEpoch: 0 })
  if (state.key !== key) setState({ key, status: 'connecting', connectionEpoch: 0 })
  useEffect(() => {
    if (!campusId) return
    const lifetime = new AbortController()
    let attempt: AbortController | undefined
    let cursor: string | undefined
    let observed: string | undefined
    let wake: (() => void) | undefined
    function refresh() {
      for (const queryKey of [
        ['graph', campusId],
        ['infrastructure', campusId],
        ['locations', campusId],
        ['reports'],
        ['admin-reports'],
        ['analytics', campusId],
        ['audit', campusId],
      ])
        void client.invalidateQueries({ queryKey })
    }
    function version(value: string, reset = false, authoritativeReset = false) {
      const newer = !observed || BigInt(value) > BigInt(observed)
      const lowered = authoritativeReset && observed && BigInt(value) < BigInt(observed)
      if (newer || lowered) {
        observed = value
        setState((previous) =>
          previous.key === key
            ? {
                ...previous,
                observedVersion: value,
                connectionEpoch: lowered ? previous.connectionEpoch + 1 : previous.connectionEpoch,
              }
            : previous,
        )
      }
      if (newer || reset) refresh()
    }
    async function confirm(signal = lifetime.signal) {
      const current = await api.graphVersion(campusId!, signal)
      if (!lifetime.signal.aborted) version(current.graph_version)
    }
    function disconnected(reason: string) {
      if (!lifetime.signal.aborted)
        setState((previous) =>
          previous.key === key
            ? { ...previous, status: 'disconnected', disconnectedReason: reason }
            : previous,
        )
    }
    function offline() {
      disconnected('Live updates disconnected. Recheck campus conditions before continuing.')
      attempt?.abort()
    }
    function resume() {
      if (document.visibilityState !== 'hidden') {
        void confirm().catch(() => {
          disconnected('Latest campus conditions could not be confirmed.')
          attempt?.abort()
        })
        wake?.()
      }
    }
    function wait(milliseconds: number) {
      return new Promise<void>((resolve) => {
        const timer = window.setTimeout(done, milliseconds)
        function done() {
          window.clearTimeout(timer)
          lifetime.signal.removeEventListener('abort', done)
          wake = undefined
          resolve()
        }
        wake = done
        lifetime.signal.addEventListener('abort', done, { once: true })
      })
    }
    async function connect() {
      let failures = 0
      while (!lifetime.signal.aborted) {
        const connection = new AbortController()
        attempt = connection
        const abort = () => connection.abort()
        lifetime.signal.addEventListener('abort', abort, { once: true })
        let lastHeartbeat = performance.now()
        let timedOut = false
        const watchdog = window.setInterval(() => {
          if (performance.now() - lastHeartbeat > 45_000) {
            timedOut = true
            disconnected('Live updates stopped responding. Recheck campus conditions.')
            connection.abort()
          }
        }, 1000)
        try {
          await consumeGraphStream(campusId!, cursor, connection.signal, {
            open: async () => {
              await confirm(connection.signal)
              if (lifetime.signal.aborted || connection.signal.aborted) return
              refresh()
              lastHeartbeat = performance.now()
              failures = 0
              setState((previous) =>
                previous.key === key
                  ? {
                      ...previous,
                      status: 'connected',
                      disconnectedReason: undefined,
                      connectionEpoch: previous.connectionEpoch + 1,
                    }
                  : previous,
              )
            },
            heartbeat: () => {
              lastHeartbeat = performance.now()
            },
            event: (event) => {
              if (lifetime.signal.aborted || connection.signal.aborted) return
              if (event.type === 'graph.updated')
                setState((previous) =>
                  previous.key === key &&
                  (!previous.lastChange ||
                    BigInt(event.id) > BigInt(previous.lastChange.graph_version))
                    ? { ...previous, lastChange: event.data }
                    : previous,
                )
              cursor =
                event.type === 'graph.reset' || !cursor || BigInt(event.id) > BigInt(cursor)
                  ? event.id
                  : cursor
              version(
                event.id,
                event.type === 'graph.reset',
                event.type === 'graph.reset' &&
                  ['cursor_reset', 'replay_gap'].includes(event.data.reason),
              )
            },
          })
        } catch {
          if (!lifetime.signal.aborted && !timedOut)
            disconnected('Live updates disconnected. Recheck campus conditions before continuing.')
        } finally {
          connection.abort()
          window.clearInterval(watchdog)
          lifetime.signal.removeEventListener('abort', abort)
        }
        if (!lifetime.signal.aborted) {
          const delay = Math.min(30_000, 1000 * 2 ** Math.min(failures++, 5))
          await wait(Math.min(30_000, delay * (0.8 + Math.random() * 0.4)))
        }
      }
    }
    window.addEventListener('offline', offline)
    window.addEventListener('online', resume)
    window.addEventListener('focus', resume)
    document.addEventListener('visibilitychange', resume)
    void connect()
    return () => {
      lifetime.abort()
      attempt?.abort()
      wake?.()
      window.removeEventListener('offline', offline)
      window.removeEventListener('online', resume)
      window.removeEventListener('focus', resume)
      document.removeEventListener('visibilitychange', resume)
    }
  }, [campusId, key, client])
  return state.key === key ? state : { key, status: 'connecting' as const, connectionEpoch: 0 }
}
