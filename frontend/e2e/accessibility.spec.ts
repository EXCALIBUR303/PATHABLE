import { audit } from './accessibility'
import { test, expect } from './fixtures'

test('public pages and mobile navigation pass automated accessibility and reflow checks', async ({
  page,
}) => {
  test.setTimeout(90_000)
  for (const path of ['/', '/navigate', '/reports', '/login', '/register']) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    if (path === '/' || path === '/navigate')
      await expect(page.locator('.leaflet-container')).toBeVisible()
    await audit(page)
    await page.setViewportSize({ width: 320, height: 800 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await audit(page)
    await page.setViewportSize({ width: 1440, height: 960 })
  }
  await page.setViewportSize({ width: 320, height: 800 })
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await audit(page)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
})

test('authenticated preferences and admin controls pass accessibility checks', async ({ page }) => {
  test.setTimeout(90_000)
  await page.goto('/login')
  await page.getByLabel('Email address').fill('browser-admin@example.com')
  await page.getByLabel('Password', { exact: true }).fill('test-only administrator password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(/dashboard/)
  for (const path of ['/dashboard', '/profile', '/admin']) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    if (path === '/admin')
      await expect(page.getByRole('button', { name: /Edit Demo/ }).first()).toBeVisible()
    await audit(page)
  }
  await page
    .getByRole('button', { name: /Edit Demo/ })
    .first()
    .click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await audit(page)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: /Edit Demo/ }).first()).toBeFocused()
})
