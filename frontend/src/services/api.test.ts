import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, fetchSession, request, setSession } from './api'
import { session } from '../test/fixtures'

beforeEach(() => {
  setSession(undefined)
  vi.unstubAllGlobals()
})
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })

describe('API client boundaries', () => {
  it('serializes session bootstrap and keeps credentials out of URLs', async () => {
    const fetch = vi.fn().mockResolvedValue(json(session))
    vi.stubGlobal('fetch', fetch)
    await Promise.all([fetchSession(), fetchSession()])
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0]?.[0]).toBe('/api/v1/auth/session')
    expect(fetch.mock.calls[0]?.[1].credentials).toBe('same-origin')
  })
  it('sends session-bound CSRF on a mutation and preserves password spaces', async () => {
    setSession(session)
    const fetch = vi.fn().mockResolvedValue(json(session))
    vi.stubGlobal('fetch', fetch)
    await api.login({ email: 'test@example.com', password: '  test password with spaces  ' })
    expect(fetch.mock.calls[0]?.[1].headers['X-CSRF-Token']).toBe('test-only-csrf')
    expect(JSON.parse(fetch.mock.calls[0]?.[1].body).password).toBe('  test password with spaces  ')
  })
  it('does not retry a stale mutation and returns the structured conflict', async () => {
    setSession(session)
    const fetch = vi.fn().mockResolvedValue(
      json(
        {
          code: 'STALE_VERSION',
          detail: 'Reload latest values',
          current_version: 2,
          request_id: 'test-request',
        },
        409,
      ),
    )
    vi.stubGlobal('fetch', fetch)
    await expect(
      api.editUser({ display_name: 'New name', expected_version: 1 }),
    ).rejects.toMatchObject({ status: 409, code: 'STALE_VERSION', currentVersion: 2 })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('honors abort signals rather than replacing cancellation with a network result', async () => {
    const controller = new AbortController()
    controller.abort()
    const fetch = vi.fn().mockRejectedValue(new DOMException('Cancelled', 'AbortError'))
    vi.stubGlobal('fetch', fetch)
    await expect(request('/campuses', { signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    })
    expect(fetch.mock.calls[0]?.[1].signal).toBe(controller.signal)
  })
  it('reports network failures honestly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network failed')))
    await expect(api.campuses()).rejects.toBeInstanceOf(ApiError)
    await expect(api.campuses()).rejects.toMatchObject({ status: 0, code: 'NETWORK_UNAVAILABLE' })
  })
  it('follows cursor pages rather than silently omitting remaining items', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ items: [{ id: 'one' }], next_cursor: 'next+page' }))
      .mockResolvedValueOnce(json({ items: [{ id: 'two' }], next_cursor: null }))
    vi.stubGlobal('fetch', fetch)
    expect(await api.campuses()).toEqual([{ id: 'one' }, { id: 'two' }])
    expect(fetch.mock.calls[1]?.[0]).toContain('cursor=next%2Bpage')
  })
})

it('sends private multipart evidence with CSRF and lets fetch generate its boundary', async () => {
  setSession(session)
  const fetch = vi.fn().mockResolvedValue(json({ id: 'image', status: 'ready' }))
  vi.stubGlobal('fetch', fetch)
  const file = new File(['image contents'], 'concern.png', { type: 'image/png' })
  await api.uploadEvidence('report', 3, file)
  const options = fetch.mock.calls[0]?.[1]
  expect(options.headers['X-CSRF-Token']).toBe('test-only-csrf')
  expect(options.headers['Content-Type']).toBeUndefined()
  expect(options.body).toBeInstanceOf(FormData)
  expect(options.body.get('expected_version')).toBe('3')
  expect(options.body.get('file').name).toBe('concern.png')
})
