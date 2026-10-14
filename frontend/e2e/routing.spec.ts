import { expect, test } from './fixtures'
import type { Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import type { RouteResult, Edge, Graph, Route } from '../src/services/api'

async function endpoints(page: Page, destination = 'Library') {
  await page.goto('/navigate')
  for (const [label, name] of [
    ['Starting point', 'Welcome'],
    ['Destination', destination],
  ]) {
    const field = page.getByRole('combobox', { name: label, exact: true })
    await field.fill(name!)
    await field.press('Enter')
  }
  await expect(page.getByRole('button', { name: 'Plan a route' })).toBeEnabled()
}

async function plan(page: Page, button = 'Plan a route'): Promise<RouteResult> {
  const pending = page.waitForResponse(
    (response) =>
      response.url().endsWith('/routes/calculate') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: button, exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  return (await response.json()) as RouteResult
}

async function shownTotals(page: Page, route: Route, warnings: RouteResult['warnings']) {
  const region = page.getByRole('region', { name: 'Route result', exact: true })
  const totals = region.locator('.route-totals')
  await expect(totals).toContainText(`${route.total_distance_m.toFixed(1)} m`)
  await expect(totals).toContainText(
    `${route.estimated_duration_s === 0 ? 0 : Math.max(1, Math.ceil(route.estimated_duration_s / 60))} min`,
  )
  for (const warning of [...warnings, ...route.warnings])
    await expect(region.getByText(warning.message, { exact: true })).toBeVisible()
  await expect(totals).toContainText(
    route.verification.summary === 'observations_current'
      ? 'Current when checked'
      : 'Contains uncertainty',
  )
  for (const instruction of route.instructions)
    await expect(region.getByText(instruction.text, { exact: true })).toBeVisible()
}

test('real routes, alternatives, metrics and both algorithms stay aligned with the API', async ({
  page,
}) => {
  await endpoints(page)
  const first = await plan(page)
  expect(first.status).toBe('found')
  if (first.status !== 'found') throw new Error('Expected seeded step-free route')
  await shownTotals(page, first.primary, first.warnings)
  await expect(page.locator('.route-line-selected')).toHaveCount(1)
  expect(first.alternatives.length).toBeGreaterThan(0)
  await page.getByRole('radio', { name: /Alternative 1/ }).check()
  await shownTotals(page, first.alternatives[0]!, first.warnings)
  await expect(page.locator('.route-line-selected')).toHaveAttribute('stroke-dasharray', '12 8')
  await page.getByLabel('Routing algorithm').selectOption('dijkstra')
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  const other = await plan(page)
  expect(other.status).toBe('found')
  if (other.status !== 'found') throw new Error('Expected Dijkstra route')
  expect(other.primary.cost_m_equivalent).toBeCloseTo(first.primary.cost_m_equivalent, 6)
  await shownTotals(page, other.primary, other.warnings)
  mkdirSync('../.local/screenshots', { recursive: true })
  await page.screenshot({ path: '../.local/screenshots/phase3-route.png', fullPage: true })
})

test('stair preference, blank entrances and same-node routes are explicit', async ({ page }) => {
  await endpoints(page)
  const stepFree = await plan(page)
  if (stepFree.status !== 'found') throw new Error('Expected step-free route')
  await page.getByRole('switch', { name: 'Avoid stairs' }).uncheck()
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  const stairs = await plan(page)
  if (stairs.status !== 'found') throw new Error('Expected stairs route')
  expect(stairs.primary.total_distance_m).toBeLessThan(stepFree.primary.total_distance_m)
  const graph: Graph = await (
    await page.request.get(`/api/v1/campuses/${stairs.campus_id}/graph`)
  ).json()
  const edges = graph.features.flatMap((feature) =>
    'source_node_id' in feature.properties ? [feature.properties as Edge] : [],
  )
  expect(
    stairs.primary.arcs.some((arc) => edges.find((edge) => edge.id === arc.edge_id)?.has_stairs),
  ).toBe(true)
  const entrance = await page.getByLabel('Starting entrance').inputValue()
  await page.getByLabel('Starting entrance').selectOption('')
  await expect(page.getByRole('button', { name: 'Plan a route' })).toBeDisabled()
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  await page.getByLabel('Starting entrance').selectOption(entrance)
  const destination = page.getByRole('combobox', { name: 'Destination', exact: true })
  await destination.fill('Welcome')
  await destination.press('Enter')
  const same = await plan(page)
  if (same.status !== 'found') throw new Error('Expected same-node result')
  expect(same.primary.geometry.type).toBe('Point')
  expect(same.primary.total_distance_m).toBe(0)
  await expect(page.locator('.route-point')).toHaveCount(1)
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  await expect(page.getByText(/Both selections use the same mapped entrance/)).toBeVisible()
})

test('unsatisfied constraints return no-route and request failures never leave a previous overlay', async ({
  page,
}) => {
  await endpoints(page)
  await page.getByText('All route preferences', { exact: true }).click()
  await page.getByLabel('Minimum width (m)', { exact: true }).fill('2')
  const result = await plan(page)
  expect(result.status).toBe('no_route')
  expect(result.primary).toBeNull()
  await expect(page.getByRole('heading', { name: 'No matching route found.' })).toBeVisible()
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  await page.getByLabel('Minimum width (m)', { exact: true }).fill('0.9')
  await plan(page)
  await expect(page.locator('.route-line-selected')).toHaveCount(1)
  await page.route('**/api/v1/routes/calculate', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/problem+json',
      body: JSON.stringify({
        code: 'ROUTING_BUDGET_EXCEEDED',
        detail: 'Route search exceeded its work budget',
      }),
    }),
  )
  await page.getByRole('button', { name: 'Plan a route' }).click()
  await expect(page.getByRole('alert')).toContainText('Route search exceeded its work budget')
  await expect(page.locator('.route-line-selected')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'No matching route found.' })).toHaveCount(0)
})

test('committed infrastructure changes invalidate a shown route and recalculate on the new revision', async ({
  page,
}) => {
  await endpoints(page)
  let initialRequest: unknown
  page.on('request', (request) => {
    if (request.url().endsWith('/routes/calculate')) initialRequest = request.postDataJSON()
  })
  const initial = await plan(page)
  if (initial.status !== 'found') throw new Error('Expected initial route')
  const bootstrap = await (await page.request.get('/api/v1/auth/session')).json()
  const logged = await page.request.post('/api/v1/auth/login', {
    headers: { Origin: 'http://localhost:5174', 'X-CSRF-Token': bootstrap.csrf_token },
    data: { email: 'browser-admin@example.com', password: 'test-only administrator password' },
  })
  expect(logged.status()).toBe(200)
  const session = await logged.json()
  const headers = { Origin: 'http://localhost:5174', 'X-CSRF-Token': session.csrf_token }
  const records = await (
    await page.request.get(`/api/v1/infrastructure?campus_id=${initial.campus_id}`)
  ).json()
  const ramp = records.items.find((item: { name: string }) => item.name === 'Demo ramp')
  const edited = await page.request.patch(`/api/v1/admin/infrastructure/${ramp.id}`, {
    headers,
    data: {
      expected_version: ramp.row_version,
      availability: 'closed',
      reason: 'Verify route invalidation for the fictional ramp',
    },
  })
  expect(edited.status()).toBe(200)
  const updated = await edited.json()
  try {
    await expect(page.getByText('Updated route ready')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.route-line-selected')).toHaveCount(0)
    const refreshed = (await (
      await page.request.post('/api/v1/routes/calculate', { data: initialRequest })
    ).json()) as RouteResult
    await page.getByRole('button', { name: 'Use updated route' }).click()
    if (refreshed.status !== 'found') throw new Error('Expected lower alternative')
    expect(BigInt(refreshed.graph_version)).toBeGreaterThan(BigInt(initial.graph_version))
    expect(refreshed.primary.arcs.some((arc) => ramp.edge_ids.includes(arc.edge_id))).toBe(false)
    await shownTotals(page, refreshed.primary, refreshed.warnings)
  } finally {
    const restored = await page.request.patch(`/api/v1/admin/infrastructure/${ramp.id}`, {
      headers,
      data: {
        expected_version: updated.row_version,
        availability: 'open',
        reason: 'Restore fictional ramp after browser check',
      },
    })
    expect(restored.status()).toBe(200)
  }
})

test('calculated routes and their text directions remain usable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await endpoints(page)
  const result = await plan(page)
  if (result.status !== 'found') throw new Error('Expected mobile route')
  await shownTotals(page, result.primary, result.warnings)
  await expect(page.getByRole('heading', { name: 'Directions as text' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../.local/screenshots/phase3-mobile-route.png', fullPage: true })
})
