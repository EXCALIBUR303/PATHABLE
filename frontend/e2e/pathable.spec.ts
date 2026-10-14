import { test, expect } from './fixtures'
import type { Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const password = 'test-only personal account password'
async function registerAndLogin(page: Page) {
  const email = `browser-${crypto.randomUUID()}@example.com`
  await page.goto('/register')
  await page.getByLabel('Your name').fill('Browser explorer')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'You’re all set.' })).toBeVisible()
  await page.getByRole('link', { name: /Sign in to continue/ }).click()
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  const loginResponse = page.waitForResponse(
    (response) => response.url().includes('/auth/login') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  const response = await loginResponse
  await response.finished()
  expect(response.status()).toBe(200)
  await expect(page).toHaveURL(/dashboard/)
  await expect(page.getByRole('heading', { name: 'Hello, Browser.' })).toBeVisible()
  const persisted = await (await page.request.get('/api/v1/auth/session')).json()
  expect(persisted.user !== null).toBe(true)
  return email
}

test('landing and keyboard map exploration render live synthetic data', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Every path/ })).toBeVisible()
  await expect(page.locator('.hero-preview .leaflet-container')).toBeVisible()
  await expect(page.locator('.hero-preview svg path.leaflet-interactive')).not.toHaveCount(0)
  mkdirSync('../.local/screenshots', { recursive: true })
  await page.screenshot({ path: '../.local/screenshots/phase2-landing.png', fullPage: true })
  await page.getByRole('link', { name: 'Explore the campus', exact: true }).click()
  const start = page.getByRole('combobox', { name: 'Starting point', exact: true })
  await start.focus()
  await start.fill('Welcome')
  await start.press('Enter')
  await expect(start).toHaveValue('Demo Welcome Centre')
  const destination = page.getByRole('combobox', { name: 'Destination', exact: true })
  await destination.focus()
  await destination.fill('Library')
  await destination.press('Enter')
  await expect(destination).toHaveValue('Demo Library')
  await page.getByRole('button', { name: 'Swap starting point and destination' }).click()
  await expect(start).toHaveValue('Demo Library')
  await expect(page.getByRole('button', { name: 'Plan a route' })).toBeEnabled()
  await page.getByText('Explore all pathways as text').click()
  await expect(page.getByRole('table')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Unknown', exact: true }).first()).toBeVisible()
  await page.screenshot({ path: '../.local/screenshots/phase2-navigation.png', fullPage: true })
  expect(errors).toEqual([])
})

test('real account preferences and saved places survive reload, then logout protects them', async ({
  page,
}) => {
  await registerAndLogin(page)
  await page.goto('/profile')
  await page.getByLabel('Minimum pathway width (m)').fill('1.1')
  await page.getByLabel('Maximum slope (%)').fill('6')
  await page.getByRole('button', { name: /Save preferences/ }).click()
  await expect(page.getByText('Your preferences have been saved.')).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Minimum pathway width (m)')).toHaveValue('1.1')
  await expect(page.getByLabel('Maximum slope (%)')).toHaveValue('6')
  await page.goto('/navigate')
  await page.getByRole('button', { name: /Library.*mapped entrance/ }).click()
  await page.getByRole('button', { name: 'Save this place' }).click()
  await expect(page.getByText('Place saved to your dashboard.')).toBeVisible()
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Demo Library', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Explore Demo Library' }).click()
  await expect(page.getByRole('heading', { name: 'Library', exact: true })).toBeVisible()
  await page.goto('/dashboard')
  await page.getByLabel('Display name').fill('Campus explorer')
  await page.getByRole('button', { name: 'Update name' }).click()
  await expect(page.getByText('Your name has been updated.')).toBeVisible()
  await page.getByRole('button', { name: /Campus explorer/ }).click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.goto('/profile')
  await expect(page).toHaveURL(/login\?returnTo/)
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
})

test('normal user cannot see admin controls or mutate infrastructure', async ({ page }) => {
  await registerAndLogin(page)
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: /for administrators/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Edit Demo/ })).toHaveCount(0)
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const campuses = await (await page.request.get('/api/v1/campuses')).json()
  const records = await (
    await page.request.get(`/api/v1/infrastructure?campus_id=${campuses.items[0].id}`)
  ).json()
  const result = await page.request.patch(`/api/v1/admin/infrastructure/${records.items[0].id}`, {
    headers: { Origin: 'http://localhost:5174', 'X-CSRF-Token': session.csrf_token },
    data: {
      expected_version: records.items[0].row_version,
      availability: 'closed',
      reason: 'Forbidden browser test',
    },
  })
  expect(result.status()).toBe(403)
})

test('admin infrastructure changes use the real API and advance graph revision', async ({
  page,
}) => {
  await page.goto('/login')
  await page.getByLabel('Email address').fill('browser-admin@example.com')
  await page.getByLabel('Password', { exact: true }).fill('test-only administrator password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(/dashboard/)
  await page.goto('/admin')
  const campus = (await (await page.request.get('/api/v1/campuses')).json()).items[0]
  const before = (
    await (await page.request.get(`/api/v1/campuses/${campus.id}/graph-version`)).json()
  ).graph_version
  await page.getByRole('button', { name: 'Edit Demo ramp' }).click()
  await page.getByLabel('Availability', { exact: true }).selectOption('temporarily_blocked')
  await page
    .getByLabel('Reason for this change')
    .fill('Browser verification of a fictional closure')
  await page.getByRole('button', { name: 'Save infrastructure change' }).click()
  await expect(
    page.getByText('Infrastructure updated. The map data has been refreshed.'),
  ).toBeVisible()
  await expect(page.getByText('temporarily blocked', { exact: true })).toBeVisible()
  const after = (
    await (await page.request.get(`/api/v1/campuses/${campus.id}/graph-version`)).json()
  ).graph_version
  expect(BigInt(after)).toBe(BigInt(before) + 1n)
  await page.getByRole('button', { name: 'Edit Demo ramp' }).click()
  await page.getByLabel('Availability', { exact: true }).selectOption('open')
  await page.getByLabel('Reason for this change').fill('Restore fictional test infrastructure')
  await page.getByRole('button', { name: 'Save infrastructure change' }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
})

test('service failure has an honest recovery state', async ({ page }) => {
  await page.route('**/api/v1/campuses?*', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/problem+json',
      body: JSON.stringify({
        code: 'DATABASE_UNAVAILABLE',
        detail: 'Campus service is temporarily unavailable.',
      }),
    }),
  )
  await page.goto('/navigate')
  await expect(page.getByRole('alert')).toHaveText(
    'We couldn’t load this.Campus service is temporarily unavailable.Try again',
  )
  await page.unroute('**/api/v1/campuses?*')
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.locator('.map-workspace .leaflet-container')).toBeVisible()
})

test('mobile navigation, focus handling, and reduced motion remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page
    .getByRole('navigation', { name: 'Mobile navigation' })
    .getByRole('link', { name: 'Explore campus' })
    .click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('heading', { name: 'Find your next place.' })).toBeVisible()
  await expect(page.locator('.map-workspace .leaflet-container')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../.local/screenshots/phase2-mobile.png', fullPage: true })
})

test('anonymous reporting requires sign-in and never claims a submission', async ({ page }) => {
  const writes: string[] = []
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/reports'))
      writes.push(request.url())
  })
  await page.goto('/reports')
  await page.getByLabel('What did you notice?').selectOption('damaged_pathway')
  await page
    .getByLabel('Tell us a little more')
    .fill('A fictional damaged pathway near the library.')
  await expect(page.getByRole('button', { name: 'Submit concern' })).toBeDisabled()
  await expect(page.getByText('Sign in to submit a concern.', { exact: true })).toBeVisible()
  expect(writes).toEqual([])
})
