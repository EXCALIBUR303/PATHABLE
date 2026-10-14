import { describe, expect, it, vi } from 'vitest'
import { consumeGraphStream, EventParser } from './stream'

const event = {
  campus_id: 'campus',
  graph_version: '42',
  changed_edge_ids: ['edge'],
  changes_truncated: false,
  reason: 'report_verified',
  occurred_at: '2026-10-13T05:00:00Z',
}
const frame = `id: 42\r\nevent: graph.updated\r\ndata: ${JSON.stringify(event)}\r\n\r\n`

describe('bounded incremental SSE transport', () => {
  it('handles split CRLF, comments and multiple committed frames without losing IDs', () => {
    const dispatch = vi.fn()
    const heartbeat = vi.fn()
    const parser = new EventParser(dispatch, heartbeat)
    parser.push(': heartbeat\r')
    parser.push('\n\n' + frame.slice(0, 13))
    parser.push(frame.slice(13) + frame)
    expect(dispatch).toHaveBeenCalledTimes(2)
    expect(dispatch.mock.calls[0]?.[0]).toEqual({ type: 'graph.updated', id: '42', data: event })
    expect(heartbeat).toHaveBeenCalledTimes(3)
  })
  it('rejects oversized lines/frames and malformed identities', () => {
    expect(() => new EventParser(vi.fn(), vi.fn()).push('data: ' + 'x'.repeat(65_536))).toThrow(
      /limit/,
    )
    const parser = new EventParser(vi.fn(), vi.fn())
    expect(() =>
      parser.push(`id: 43\nevent: graph.updated\ndata: ${JSON.stringify(event)}\n\n`),
    ).toThrow(/payload/)
  })
  it('treats stream failures as disconnection rather than a successful graph message', () => {
    expect(() =>
      new EventParser(vi.fn(), vi.fn()).push(
        'event: stream.error\ndata: {"code":"STREAM_UNAVAILABLE"}\n\n',
      ),
    ).toThrow(/unavailable/)
  })
  it('carries cursor in a header, uses cookies, revalidates before dispatch and cancels the reader', async () => {
    const order: string[] = []
    const cancel = vi.fn()
    const encoded = new TextEncoder().encode(frame)
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoded.slice(0, 31))
        controller.enqueue(encoded.slice(31))
        controller.close()
      },
      cancel,
    })
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }))
    const dispatch = vi.fn(() => order.push('event'))
    await expect(
      consumeGraphStream(
        'campus',
        '41',
        new AbortController().signal,
        {
          open: async () => {
            order.push('confirmed')
          },
          event: dispatch,
          heartbeat: vi.fn(),
        },
        fetcher,
      ),
    ).rejects.toThrow(/closed/)
    expect(order).toEqual(['confirmed', 'event'])
    expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/campuses/campus/events')
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      credentials: 'same-origin',
      headers: { 'Last-Event-ID': '41' },
    })
    expect(dispatch).toHaveBeenCalledWith({ type: 'graph.updated', id: '42', data: event })
  })
  it('rejects a valid frame for another campus', async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(frame))
        controller.close()
      },
    })
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }))
    await expect(
      consumeGraphStream(
        'other',
        '41',
        new AbortController().signal,
        { open: async () => undefined, event: vi.fn(), heartbeat: vi.fn() },
        fetcher,
      ),
    ).rejects.toThrow(/campus/)
  })
})

it('aborts a stalled body immediately even when its cancellation promise never settles', async () => {
  const controller = new AbortController()
  let opened!: (value?: unknown) => void
  const ready = new Promise((resolve) => {
    opened = resolve
  })
  const cancel = vi.fn(() => new Promise<void>(() => undefined))
  const body = new ReadableStream<Uint8Array>({ cancel })
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }))
  const pending = consumeGraphStream(
    'campus',
    undefined,
    controller.signal,
    {
      open: async () => {
        opened()
      },
      event: vi.fn(),
      heartbeat: vi.fn(),
    },
    fetcher,
  )
  await ready
  await Promise.resolve()
  controller.abort()
  await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
  expect(cancel).toHaveBeenCalledTimes(1)
})
