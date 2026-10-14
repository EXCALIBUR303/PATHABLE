import { expect, it, vi } from 'vitest'
import { fetchSession, request, setSession } from './api'
import { session } from '../test/fixtures'

it('a delayed old session response cannot replace a newer authenticated session', async () => {
  setSession(undefined)
  let deliver: (response: Response) => void = () => undefined
  const delayed = new Promise<Response>((resolve) => {
    deliver = resolve
  })
  const fetch = vi
    .fn()
    .mockReturnValueOnce(delayed)
    .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  const old = fetchSession()
  setSession({ ...session, csrf_token: 'new-test-session' })
  deliver(
    new Response(JSON.stringify({ ...session, user: null, csrf_token: 'old-test-session' }), {
      status: 200,
    }),
  )
  await expect(old).rejects.toMatchObject({ name: 'AbortError' })
  await request('/me', { method: 'PATCH', body: { display_name: 'New name', expected_version: 1 } })
  expect(fetch.mock.calls[1]?.[1].headers['X-CSRF-Token']).toBe('new-test-session')
  vi.unstubAllGlobals()
  setSession(undefined)
})
