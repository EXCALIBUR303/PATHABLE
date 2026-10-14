export type GraphEvent = {
  campus_id: string
  graph_version: string
  changed_edge_ids: string[]
  changes_truncated: boolean
  reason: string
  occurred_at: string
}
export type StreamEvent = { type: 'graph.updated' | 'graph.reset'; id: string; data: GraphEvent }

// Incremental framing handles split UTF-8/CRLF and bounded server frames.
export class EventParser {
  private buffer = ''
  private event = ''
  private id = ''
  private data: string[] = []
  private size = 0
  constructor(
    private dispatch: (event: StreamEvent) => void,
    private heartbeat: () => void,
  ) {}
  push(chunk: string) {
    this.buffer += chunk
    let boundary: number
    while ((boundary = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, boundary).replace(/\r$/, '')
      this.buffer = this.buffer.slice(boundary + 1)
      this.size += line.length
      if (this.size > 65_536) throw new Error('Live update frame exceeds its limit')
      if (line === '') {
        if (this.event === 'stream.error') throw new Error('Live update service unavailable')
        if (this.data.length) {
          if (
            !['graph.updated', 'graph.reset'].includes(this.event) ||
            !/^[1-9][0-9]{0,18}$/.test(this.id)
          )
            throw new Error('Invalid live update')
          const data = JSON.parse(this.data.join('\n')) as GraphEvent
          if (
            data.graph_version !== this.id ||
            !Array.isArray(data.changed_edge_ids) ||
            data.changed_edge_ids.length > 200 ||
            data.changed_edge_ids.some((id) => typeof id !== 'string') ||
            typeof data.campus_id !== 'string' ||
            typeof data.reason !== 'string' ||
            !Number.isFinite(Date.parse(data.occurred_at))
          )
            throw new Error('Invalid live update payload')
          this.dispatch({ type: this.event as StreamEvent['type'], id: this.id, data })
          this.heartbeat()
        }
        this.event = ''
        this.id = ''
        this.data = []
        this.size = 0
      } else if (line.startsWith(':')) {
        this.heartbeat()
      } else {
        const colon = line.indexOf(':')
        const field = colon < 0 ? line : line.slice(0, colon)
        const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '')
        if (field === 'event') this.event = value
        if (field === 'id') this.id = value
        if (field === 'data') this.data.push(value)
      }
    }
    if (this.buffer.length > 65_536) throw new Error('Live update line exceeds its limit')
  }
}

export async function consumeGraphStream(
  campusId: string,
  cursor: string | undefined,
  signal: AbortSignal,
  callbacks: {
    open: () => Promise<void>
    event: (event: StreamEvent) => void
    heartbeat: () => void
  },
  fetcher: typeof fetch = fetch,
) {
  const response = await fetcher(`/api/v1/campuses/${campusId}/events`, {
    headers: { Accept: 'text/event-stream', ...(cursor ? { 'Last-Event-ID': cursor } : {}) },
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
  })
  if (
    !response.ok ||
    !response.body ||
    !response.headers.get('content-type')?.includes('text/event-stream')
  )
    throw new Error('Live update connection unavailable')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = new EventParser((event) => {
    if (event.data.campus_id !== campusId) throw new Error('Unexpected campus update')
    callbacks.event(event)
  }, callbacks.heartbeat)
  let onAbort!: () => void
  const interrupted = new Promise<never>((_resolve, reject) => {
    onAbort = () => reject(new DOMException('Live update request cancelled', 'AbortError'))
    signal.addEventListener('abort', onAbort, { once: true })
    if (signal.aborted) onAbort()
  })
  try {
    await Promise.race([callbacks.open(), interrupted])
    while (!signal.aborted) {
      const { value, done } = await Promise.race([reader.read(), interrupted])
      if (done) throw new Error('Live update connection closed')
      parser.push(decoder.decode(value, { stream: true }))
    }
    throw new DOMException('Live update request cancelled', 'AbortError')
  } finally {
    signal.removeEventListener('abort', onAbort)
    // Cancellation must not wait for a stalled network/body source to acknowledge it.
    void reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
