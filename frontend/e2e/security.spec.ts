import { test, expect } from './fixtures'

test('proxied browser sessions enforce CSRF, private ownership, roles and plain-text reports', async ({
  page,
  browser,
}) => {
  const base = '/api/v1'
  const bootstrap = await page.request.get(`${base}/auth/session`)
  expect(bootstrap.headers()['cache-control']).toBe('no-store')
  expect(bootstrap.headers()['x-content-type-options']).toBe('nosniff')
  const initial = await bootstrap.json()
  const headers = { Origin: 'http://localhost:5174', 'X-CSRF-Token': initial.csrf_token }
  const email = `security-${crypto.randomUUID()}@example.com`
  const password = 'test-only security account password'
  const registration = { email, password, display_name: 'Security explorer' }
  expect(
    (
      await page.request.post(`${base}/auth/register`, {
        headers: { ...headers, Origin: 'https://untrusted.example' },
        data: registration,
      })
    ).status(),
  ).toBe(403)
  expect(
    (
      await page.request.post(`${base}/auth/register`, {
        headers: { Origin: headers.Origin },
        data: registration,
      })
    ).status(),
  ).toBe(403)
  expect(
    (await page.request.post(`${base}/auth/register`, { headers, data: registration })).status(),
  ).toBe(201)
  const login = await page.request.post(`${base}/auth/login`, {
    headers,
    data: { email, password },
  })
  expect(login.status()).toBe(200)
  const authenticated = await login.json()
  headers['X-CSRF-Token'] = authenticated.csrf_token
  expect(authenticated.csrf_token).not.toBe(initial.csrf_token)
  const cookies = await page.context().cookies()
  const cookie = cookies.find((value) => value.name === 'pathable_session')!
  expect(cookie.httpOnly).toBe(true)
  expect(cookie.sameSite).toBe('Lax')
  const campus = (await (await page.request.get(`${base}/campuses`)).json()).items[0]
  const location = (
    await (await page.request.get(`${base}/locations?campus_id=${campus.id}`)).json()
  ).items[0]
  const description = '<img src=x onerror="window.reportInjected=true"> Fictional test concern'
  const created = await page.request.post(`${base}/reports`, {
    headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
    data: {
      campus_id: campus.id,
      location_id: location.id,
      point: location.point,
      category: 'other_accessibility_concern',
      description,
    },
  })
  expect(created.status()).toBe(201)
  const report = await created.json()
  expect(
    (
      await page.request.post(`${base}/admin/reports/${report.id}/review`, {
        headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
        data: {
          decision: 'reject',
          expected_version: report.row_version,
          reason: 'Forbidden ordinary user review',
        },
      })
    ).status(),
  ).toBe(403)
  const other = await browser.newContext({ baseURL: 'http://localhost:5174' })
  try {
    const session = await (await other.request.get(`${base}/auth/session`)).json()
    const h = { Origin: headers.Origin, 'X-CSRF-Token': session.csrf_token }
    const identity = {
      email: `other-${crypto.randomUUID()}@example.com`,
      password,
      display_name: 'Other explorer',
    }
    expect(
      (await other.request.post(`${base}/auth/register`, { headers: h, data: identity })).status(),
    ).toBe(201)
    expect(
      (
        await other.request.post(`${base}/auth/login`, {
          headers: h,
          data: { email: identity.email, password },
        })
      ).status(),
    ).toBe(200)
    for (const suffix of ['', '/predictions']) {
      expect((await other.request.get(`${base}/reports/${report.id}${suffix}`)).status()).toBe(404)
    }
  } finally {
    await other.close()
  }
  await page.goto('/reports')
  await expect(page.getByText(description, { exact: true })).toBeVisible()
  expect(await page.evaluate(() => 'reportInjected' in window)).toBe(false)
  expect((await page.request.get(`${base}/reports/${report.id}`)).status()).toBe(200)
  expect((await page.request.post(`${base}/auth/logout`, { headers })).status()).toBe(204)
  expect((await page.request.get(`${base}/reports/${report.id}`)).status()).toBe(401)
})
