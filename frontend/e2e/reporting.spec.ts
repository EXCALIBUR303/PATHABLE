import { audit } from './accessibility'
import { test, expect } from './fixtures'
import type { Browser, Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import type { Report, RouteRequest, RouteResult } from '../src/services/api'

const password = 'test-only reporting account password'
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
)
const image = { name: 'fictional-concern.png', mimeType: 'image/png', buffer: png }
async function account(page: Page, admin = false) {
  const email = admin ? 'browser-admin@example.com' : `report-${crypto.randomUUID()}@example.com`
  const bootstrap = await (await page.request.get('/api/v1/auth/session')).json()
  let headers = { Origin: 'http://localhost:5174', 'X-CSRF-Token': bootstrap.csrf_token }
  if (!admin) {
    const created = await page.request.post('/api/v1/auth/register', {
      headers,
      data: { email, password, display_name: 'Report explorer' },
    })
    expect(created.status()).toBe(201)
  }
  const result = await page.request.post('/api/v1/auth/login', {
    headers,
    data: { email, password: admin ? 'test-only administrator password' : password },
  })
  expect(result.status()).toBe(200)
  const session = await result.json()
  headers = { Origin: 'http://localhost:5174', 'X-CSRF-Token': session.csrf_token }
  return headers
}
async function adminPage(browser: Browser) {
  const context = await browser.newContext({ baseURL: 'http://localhost:5174' })
  const page = await context.newPage()
  const headers = await account(page, true)
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Report review', exact: true })).toBeVisible()
  return { context, page, headers }
}
async function route(page: Page) {
  await page.goto('/navigate')
  await expect(page.getByText('Live campus updates connected.', { exact: true })).toBeVisible()
  for (const [label, name] of [
    ['Starting point', 'Welcome'],
    ['Destination', 'Library'],
  ]) {
    const field = page.getByRole('combobox', { name: label, exact: true })
    await field.fill(name!)
    await field.press('Enter')
    await expect(field).toHaveValue(name === 'Welcome' ? 'Demo Welcome Centre' : 'Demo Library')
  }
  await expect(page.getByText('Live campus updates connected.', { exact: true })).toBeVisible()
  const pending = page.waitForResponse(
    (response) =>
      response.url().endsWith('/routes/calculate') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Plan a route' }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  const result = (await response.json()) as RouteResult
  expect(result.status).toBe('found')
  await expect(page.locator('.route-line-selected')).toHaveCount(1)
  return { result, request: response.request().postDataJSON() as RouteRequest }
}
async function apiReport(page: Page, headers: Record<string, string>, category = 'blocked_ramp') {
  const campuses = await (await page.request.get('/api/v1/campuses')).json()
  const campus = campuses.items[0]
  const infrastructure = await (
    await page.request.get(`/api/v1/infrastructure?campus_id=${campus.id}`)
  ).json()
  const ramp = infrastructure.items.find((item: { name: string }) => item.name === 'Demo ramp')
  const response = await page.request.post('/api/v1/reports', {
    headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
    data: {
      campus_id: campus.id,
      category,
      description: 'Fictional concern for browser integration checks.',
      point: ramp.point,
      infrastructure_id: ramp.id,
      suggested_edge_ids: ramp.edge_ids,
    },
  })
  expect(response.status()).toBe(201)
  return { report: (await response.json()) as Report, ramp, campus }
}
async function cleanup(page: Page, headers: Record<string, string>, id: string) {
  const response = await page.request.get(`/api/v1/reports/${id}`)
  if (response.status() !== 200) return
  const report = (await response.json()) as Report
  if (report.status === 'verified') {
    const result = await page.request.post(`/api/v1/admin/reports/${id}/resolve`, {
      headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
      data: {
        expected_version: report.row_version,
        reason: 'Restore fictional browser-test pathways',
      },
    })
    expect(result.status()).toBe(200)
  }
}

test('real submission, private evidence, review, analytics and live rerouting form one pipeline', async ({
  page,
  browser,
}) => {
  test.setTimeout(60_000)
  await account(page)
  await page.goto('/reports')
  await page.getByLabel('Where is the concern?').selectOption({ label: 'Demo Welcome Centre' })
  await page.getByLabel('Related infrastructure (optional)').selectOption({ label: 'Demo ramp' })
  await page
    .getByLabel('Tell us a little more')
    .fill('Fictional ramp blocked for end-to-end verification.')
  await page.getByLabel('Supporting image (optional)').setInputFiles(image)
  const submitted = page.waitForResponse(
    (response) => response.url().endsWith('/reports') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Submit concern' }).click()
  const response = await submitted
  expect(response.status()).toBe(201)
  const report = (await response.json()) as Report
  await expect(page.getByText(/Report submitted for administrator review/)).toBeVisible()
  const card = page.getByRole('article', { name: 'Report: Blocked ramp' })
  await expect(card.getByRole('img')).toBeVisible()
  const contentUrl = await card.getByRole('img').getAttribute('src')
  expect((await page.request.get(contentUrl!)).status()).toBe(200)
  const navigation = await page.context().newPage()
  const original = await route(navigation)
  const admin = await adminPage(browser)
  try {
    const row = admin.page
      .getByRole('row')
      .filter({ hasText: 'Fictional ramp blocked for end-to-end verification.' })
    await row.getByRole('button', { name: 'Review concern', exact: true }).click()
    await admin.page
      .getByLabel('Review reason', { exact: true })
      .fill('Confirmed fictional obstacle and affected ramp walkway')
    const revised = navigation.waitForResponse(
      (response) =>
        response.url().endsWith('/routes/calculate') && response.request().method() === 'POST',
    )
    const reviewed = admin.page.waitForResponse((response) =>
      response.url().endsWith(`/reports/${report.id}/review`),
    )
    await audit(admin.page)
    const mutationStartedAt = Date.now()
    await admin.page.getByRole('button', { name: 'Verify concern', exact: true }).click()
    const reviewedResponse = await reviewed
    expect(reviewedResponse.status()).toBe(200)
    const verifiedReport = (await reviewedResponse.json()) as Report
    expect(verifiedReport.confirmed_edge_ids.length).toBeGreaterThan(0)
    await expect(navigation.locator('.route-line-selected')).toHaveCount(0)
    const invalidatedMs = Date.now() - mutationStartedAt
    expect(invalidatedMs).toBeLessThan(2000)
    const recalculated = (await (await revised).json()) as RouteResult
    expect(recalculated.status).toBe('found')
    if (recalculated.status !== 'found') throw new Error('Expected lower alternative')
    expect(BigInt(recalculated.graph_version)).toBeGreaterThan(
      BigInt(original.result.graph_version),
    )
    expect(recalculated.accessibility_profile).toEqual(original.request.accessibility_profile)
    expect(
      recalculated.primary.arcs.some((arc) =>
        verifiedReport.confirmed_edge_ids.includes(arc.edge_id),
      ),
    ).toBe(false)
    await expect(navigation.getByText('Updated route ready', { exact: true })).toBeVisible()
    await expect(
      navigation.getByText('A mapped change affects your previous route.', { exact: false }),
    ).toBeVisible()
    await expect(navigation.locator('.route-line-selected')).toHaveCount(0)
    await navigation.getByRole('button', { name: 'Use updated route' }).click()
    await expect(navigation.locator('.route-line-selected')).toHaveCount(1)
    await expect(page.getByText('Verified concern', { exact: true })).toBeVisible()
    await expect(admin.page.getByRole('region', { name: 'Campus analytics' })).toBeVisible()
    const analytics = await (
      await admin.page.request.get(
        `/api/v1/admin/analytics?campus_id=${report.campus_id}&from=${new Date(Date.now() - 86400_000).toISOString()}&to=${new Date(Date.now() + 86400_000).toISOString()}`,
      )
    ).json()
    expect(analytics.active_verified_obstacles).toBeGreaterThan(0)
    await expect(
      admin.page
        .locator('.analytics-metrics')
        .getByText(String(analytics.active_verified_obstacles), { exact: true })
        .first(),
    ).toBeVisible()
    await expect(
      admin.page
        .getByRole('region', { name: 'Administrative audit history' })
        .getByText('Confirmed fictional obstacle and affected ramp walkway', { exact: true }),
    ).toBeVisible()
    await audit(admin.page)
    await audit(page)
    mkdirSync('../.local/screenshots', { recursive: true })
    await admin.page.screenshot({ path: '../.local/screenshots/phase4-admin.png', fullPage: true })
    await page.screenshot({ path: '../.local/screenshots/phase4-reports.png', fullPage: true })
    await admin.page.getByLabel('Report status', { exact: true }).selectOption('verified')
    await admin.page
      .getByRole('row')
      .filter({ hasText: 'Fictional ramp blocked for end-to-end verification.' })
      .getByRole('button', { name: 'Resolve concern', exact: true })
      .click()
    await admin.page
      .getByLabel('Resolution reason', { exact: true })
      .fill('Fictional obstacle removed after browser validation')
    await admin.page.getByRole('button', { name: 'Resolve concern', exact: true }).last().click()
    await expect(admin.page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByText('Resolved', { exact: true })).toBeVisible()
    await expect(navigation.getByText('Updated route ready', { exact: true })).toBeVisible()
    await navigation.getByRole('button', { name: 'Use updated route' }).click()
    const version = await (
      await navigation.request.get(`/api/v1/campuses/${report.campus_id}/graph-version`)
    ).json()
    const result = (await (
      await navigation.request.post('/api/v1/routes/calculate', { data: original.request })
    ).json()) as RouteResult
    expect(result.graph_version).toBe(version.graph_version)
    console.log(`Observed report-to-client invalidation: ${invalidatedMs} ms`)
  } finally {
    await cleanup(admin.page, admin.headers, report.id)
    await navigation.close()
    await admin.context.close()
  }
})

test('a stale review preserves the draft and cannot duplicate restrictions', async ({
  page,
  browser,
}) => {
  await account(page)
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const { report, ramp } = await apiReport(page, {
    Origin: 'http://localhost:5174',
    'X-CSRF-Token': session.csrf_token,
  })
  const admin = await adminPage(browser)
  try {
    await admin.page
      .getByRole('row')
      .filter({ hasText: report.description })
      .getByRole('button', { name: 'Review concern' })
      .last()
      .click()
    await admin.page.getByLabel('Review reason').fill('Preserve this unsaved review explanation')
    const winner = await admin.page.request.post(`/api/v1/admin/reports/${report.id}/review`, {
      headers: { ...admin.headers, 'Idempotency-Key': crypto.randomUUID() },
      data: {
        expected_version: 1,
        decision: 'verify',
        confirmed_edge_ids: ramp.edge_ids,
        reason: 'Independent winning review',
      },
    })
    expect(winner.status()).toBe(200)
    const before = await (
      await admin.page.request.get(`/api/v1/campuses/${report.campus_id}/graph-version`)
    ).json()
    const failure = admin.page.waitForResponse((response) =>
      response.url().endsWith(`/reports/${report.id}/review`),
    )
    await admin.page.getByRole('button', { name: 'Verify concern' }).click()
    expect((await failure).status()).toBe(409)
    await expect(admin.page.getByRole('alert')).toContainText('Resource changed')
    await expect(admin.page.getByLabel('Review reason')).toHaveValue(
      'Preserve this unsaved review explanation',
    )
    const after = await (
      await admin.page.request.get(`/api/v1/campuses/${report.campus_id}/graph-version`)
    ).json()
    expect(after.graph_version).toBe(before.graph_version)
    const latest = (await (
      await admin.page.request.get(`/api/v1/reports/${report.id}`)
    ).json()) as Report
    expect(latest.history.filter((event) => event.to_status === 'verified')).toHaveLength(1)
  } finally {
    await cleanup(admin.page, admin.headers, report.id)
    await admin.context.close()
  }
})

test('invalid image content has a recoverable private-upload state and another owner cannot read it', async ({
  page,
  browser,
}) => {
  const headers = await account(page)
  const { report } = await apiReport(page, headers, 'damaged_pathway')
  await page.goto('/reports')
  const card = page.getByRole('article', { name: 'Report: Damaged pathway' })
  await card.getByLabel(/Add supporting image/).setInputFiles({
    name: 'fake.png',
    mimeType: 'image/png',
    buffer: Buffer.from('<svg>not a PNG</svg>'),
  })
  await card.getByRole('button', { name: 'Upload image' }).click()
  await expect(card.getByRole('alert')).toContainText('Image could not be accepted')
  await expect(card.getByText('This image was not accepted.')).toBeVisible()
  await card.getByLabel(/Add supporting image/).setInputFiles(image)
  await card.getByRole('button', { name: 'Upload image' }).click()
  await expect(card.getByRole('img')).toBeVisible()
  const url = await card.getByRole('img').getAttribute('src')
  const otherContext = await browser.newContext({ baseURL: 'http://localhost:5174' })
  try {
    const other = await otherContext.newPage()
    await account(other)
    expect((await other.request.get(url!)).status()).toBe(404)
    expect((await other.request.get(`/api/v1/reports/${report.id}`)).status()).toBe(404)
  } finally {
    await otherContext.close()
  }
  await card
    .locator('.report-evidence-item')
    .filter({ has: page.getByRole('img') })
    .getByRole('button', { name: 'Remove supporting image' })
    .click()
  await expect(card.getByRole('img')).toHaveCount(0)
  expect((await page.request.get(url!)).status()).toBe(404)
})

test('a real verified barrier can cause honest no-route and committed events replay after disconnection', async ({
  page,
  browser,
}) => {
  await account(page)
  const original = await route(page)
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const { report } = await apiReport(
    page,
    { Origin: 'http://localhost:5174', 'X-CSRF-Token': session.csrf_token },
    'temporary_obstacle',
  )
  const admin = await adminPage(browser)
  try {
    const graph = await (
      await admin.page.request.get(`/api/v1/campuses/${report.campus_id}/graph`)
    ).json()
    const edgeIds = graph.features
      .filter((feature: { geometry: { type: string } }) => feature.geometry.type === 'LineString')
      .map((feature: { id: string }) => feature.id)
    const revised = page.waitForResponse(
      (response) =>
        response.url().endsWith('/routes/calculate') && response.request().method() === 'POST',
    )
    const verified = await admin.page.request.post(`/api/v1/admin/reports/${report.id}/review`, {
      headers: { ...admin.headers, 'Idempotency-Key': crypto.randomUUID() },
      data: {
        expected_version: 1,
        decision: 'verify',
        confirmed_edge_ids: edgeIds,
        restriction_kind: 'closed',
        reason: 'Fictional closure of every mapped connection',
      },
    })
    expect(verified.status()).toBe(200)
    const result = (await (await revised).json()) as RouteResult
    expect(result.status).toBe('no_route')
    expect(result.primary).toBeNull()
    await expect(page.getByRole('heading', { name: 'No matching route found.' })).toBeVisible()
    await expect(page.locator('.route-line-selected')).toHaveCount(0)
    const replay = await page.evaluate(
      async ({ campus, cursor }) => {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 5000)
        try {
          const response = await fetch(`/api/v1/campuses/${campus}/events`, {
            headers: { 'Last-Event-ID': cursor, Accept: 'text/event-stream' },
            signal: controller.signal,
          })
          const reader = response.body!.getReader()
          const decoder = new TextDecoder()
          let data = ''
          try {
            while (!data.includes('\n\n')) {
              const chunk = await reader.read()
              if (chunk.done) throw new Error('Missing replay frame')
              data += decoder.decode(chunk.value, { stream: true })
            }
            return data.split('\n\n')[0]
          } finally {
            await reader.cancel()
          }
        } finally {
          clearTimeout(timeout)
          controller.abort()
        }
      },
      { campus: report.campus_id, cursor: original.result.graph_version },
    )
    expect(replay).toContain('event: graph.updated')
    expect(replay).toContain('report_verified')
    expect(replay).not.toContain(report.description)
  } finally {
    await cleanup(admin.page, admin.headers, report.id)
    await admin.context.close()
  }
})

test('offline interruption retires guidance and reconnect revalidates the unchanged trip', async ({
  page,
  context,
}) => {
  const original = await route(page)
  await context.setOffline(true)
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  await expect(page.getByText(/Live updates disconnected/).first()).toBeVisible()
  await context.setOffline(false)
  await expect(page.getByText('Updated route ready', { exact: true })).toBeVisible({
    timeout: 15_000,
  })
  await page.getByRole('button', { name: 'Use updated route' }).click()
  await expect(page.locator('.route-line-selected')).toHaveCount(1)
  await expect(page.getByRole('combobox', { name: 'Starting point', exact: true })).toHaveValue(
    'Demo Welcome Centre',
  )
  expect(original.request.accessibility_profile.avoid_stairs).toBe(true)
})

test('mobile reporting remains usable with reduced motion and real persisted history', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await account(page)
  await page.goto('/reports')
  await page.getByLabel('Where is the concern?').selectOption({ label: 'Demo Library' })
  await page.getByLabel('What did you notice?').selectOption('inaccessible_entrance')
  await page
    .getByLabel('Tell us a little more')
    .fill('Fictional entrance concern from mobile browser.')
  await page.getByRole('button', { name: 'Submit concern' }).click()
  const card = page.getByRole('article', { name: 'Report: Inaccessible entrance' })
  await expect(card.getByText('Awaiting review')).toBeVisible()
  await card.getByText('Review history', { exact: true }).click()
  await expect(card.getByText('Awaiting administrator review')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../.local/screenshots/phase4-mobile-reports.png', fullPage: true })
})
