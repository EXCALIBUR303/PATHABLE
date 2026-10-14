import { audit } from './accessibility'
import { test, expect } from './fixtures'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { mkdirSync } from 'node:fs'

test('unavailable inference preserves manual reporting; synthetic annotation review cannot change routes', async ({
  page,
  browser,
}) => {
  const base = '/api/v1'
  const email = `ml-boundary-${crypto.randomUUID()}@example.com`
  const password = 'test-only optional ML account password'
  const bootstrap = await (await page.request.get(`${base}/auth/session`)).json()
  const headers = { Origin: 'http://localhost:5174', 'X-CSRF-Token': bootstrap.csrf_token }
  expect(
    (
      await page.request.post(`${base}/auth/register`, {
        headers,
        data: { email, password, display_name: 'ML boundary explorer' },
      })
    ).status(),
  ).toBe(201)
  const session = await (
    await page.request.post(`${base}/auth/login`, { headers, data: { email, password } })
  ).json()
  const owner = { ...headers, 'X-CSRF-Token': session.csrf_token }
  const campus = (await (await page.request.get(`${base}/campuses`)).json()).items[0]
  const location = (
    await (await page.request.get(`${base}/locations?campus_id=${campus.id}`)).json()
  ).items[0]
  const created = await page.request.post(`${base}/reports`, {
    headers: { ...owner, 'Idempotency-Key': crypto.randomUUID() },
    data: {
      campus_id: campus.id,
      location_id: location.id,
      point: location.point,
      category: 'other_accessibility_concern',
      description: 'Synthetic ML annotation boundary concern',
    },
  })
  expect(created.status()).toBe(201)
  const report = await created.json()
  const bytes = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    'base64',
  )
  const uploaded = await page.request.post(`${base}/reports/${report.id}/evidence`, {
    headers: owner,
    multipart: {
      expected_version: String(report.row_version),
      file: { name: 'fixture.png', mimeType: 'image/png', buffer: bytes },
    },
  })
  expect(uploaded.status()).toBe(201)
  const image = await uploaded.json()
  const before = (
    await (await page.request.get(`${base}/campuses/${campus.id}/graph-version`)).json()
  ).graph_version
  expect((await (await page.request.get(`${base}/ml/status`)).json()).available).toBe(false)
  const unavailable = await page.request.post(`${base}/reports/${report.id}/inference`, {
    headers: { ...owner, 'Idempotency-Key': crypto.randomUUID() },
    data: { evidence_id: image.id },
  })
  expect(unavailable.status()).toBe(503)
  expect((await unavailable.json()).code).toBe('ML_UNAVAILABLE')
  execFileSync(
    resolve('../.venv/bin/python'),
    [resolve('../scripts/e2e_ml_fixture.py'), report.id, image.id],
    { cwd: resolve('..'), stdio: 'pipe' },
  )
  await page.goto('/reports')
  const card = page.getByRole('article').filter({ hasText: report.description })
  await card.getByText('Image analysis', { exact: true }).click()
  await expect(card.getByText(/Image analysis is currently unavailable/)).toBeVisible()
  await expect(card.getByText('Visible stairs', { exact: true })).toBeVisible()
  await expect(card.getByText(/Synthetic test fixture/).first()).toBeVisible()
  await expect(card.getByRole('button', { name: 'Review Visible stairs' })).toHaveCount(0)
  const context = await browser.newContext({ baseURL: 'http://localhost:5174' })
  try {
    const adminPage = await context.newPage()
    const anonymous = await (await adminPage.request.get(`${base}/auth/session`)).json()
    const login = await adminPage.request.post(`${base}/auth/login`, {
      headers: { Origin: 'http://localhost:5174', 'X-CSRF-Token': anonymous.csrf_token },
      data: { email: 'browser-admin@example.com', password: 'test-only administrator password' },
    })
    expect(login.status()).toBe(200)
    const admin = (await login.json()).csrf_token
    await adminPage.goto('/admin')
    await adminPage
      .getByRole('row')
      .filter({ hasText: report.description })
      .getByRole('button', { name: /Review/ })
      .click()
    const dialog = adminPage.getByRole('dialog')
    await dialog.getByText('Image analysis', { exact: true }).click()
    await dialog.getByRole('button', { name: 'Review Visible stairs' }).click()
    await dialog
      .getByLabel('Annotation review reason')
      .fill('Accept synthetic image annotation only')
    await audit(adminPage)
    await dialog.getByRole('button', { name: 'Accept annotation' }).click()
    await expect(
      dialog.getByText('Annotation review saved. Route conditions have not changed.'),
    ).toBeVisible()
    await expect(dialog.getByText('accepted', { exact: true })).toBeVisible()
    expect(
      (await (await page.request.get(`${base}/campuses/${campus.id}/graph-version`)).json())
        .graph_version,
    ).toBe(before)
    expect((await (await page.request.get(`${base}/reports/${report.id}`)).json()).status).toBe(
      'pending_review',
    )
    mkdirSync(resolve('../.local/screenshots'), { recursive: true })
    await adminPage.screenshot({
      path: resolve('../.local/screenshots/phase5-annotation-review.png'),
      fullPage: true,
    })
    const current = await (await adminPage.request.get(`${base}/reports/${report.id}`)).json()
    expect(
      (
        await adminPage.request.post(`${base}/admin/reports/${report.id}/review`, {
          headers: {
            Origin: 'http://localhost:5174',
            'X-CSRF-Token': admin,
            'Idempotency-Key': crypto.randomUUID(),
          },
          data: {
            decision: 'reject',
            expected_version: current.row_version,
            reason: 'Complete synthetic boundary scenario without a restriction',
          },
        })
      ).status(),
    ).toBe(200)
  } finally {
    await context.close()
  }
})
