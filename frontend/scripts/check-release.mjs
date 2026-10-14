import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const [base, certificate, screenshot] = process.argv.slice(2)
assert(
  base && certificate && screenshot,
  'Supply HTTPS origin, trusted local fixture certificate and screenshot path',
)
const publicKey = execFileSync('openssl', ['x509', '-in', certificate, '-pubkey', '-noout'])
const der = execFileSync('openssl', ['pkey', '-pubin', '-outform', 'DER'], { input: publicKey })
const pin = createHash('sha256').update(der).digest('base64')
const executablePath =
  process.env.PATHABLE_CHROMIUM_PATH ??
  (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined)
const browser = await chromium.launch({
  ...(executablePath ? { executablePath } : {}),
  // Trust only this generated localhost certificate key; the Python smoke also
  // verifies its full certificate chain, host and validity. No blanket ignore.
  args: [`--ignore-certificate-errors-spki-list=${pin}`],
})
try {
  const context = await browser.newContext({
    baseURL: base,
    viewport: { width: 1440, height: 960 },
  })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error' && message.text().includes('Content Security Policy'))
      errors.push(message.text())
  })
  await page.goto('/navigate')
  await page.getByRole('heading', { name: 'Find your next place.' }).waitFor()
  await page.locator('.leaflet-container').waitFor()
  const start = page.getByRole('combobox', { name: 'Starting point', exact: true })
  await start.fill('Welcome')
  await start.press('Enter')
  const destination = page.getByRole('combobox', { name: 'Destination', exact: true })
  await destination.fill('Library')
  await destination.press('Enter')
  const calculation = page.waitForResponse((response) =>
    response.url().endsWith('/routes/calculate'),
  )
  await page.getByRole('button', { name: 'Plan a route' }).click()
  const response = await calculation
  const route = await response.json()
  assert.equal(response.status(), 200)
  assert.equal(route.status, 'found', JSON.stringify({ status: route.status, errors }))
  const selectedLine = page.locator('.route-line-selected')
  try {
    await selectedLine.waitFor({ state: 'attached' })
  } catch (error) {
    mkdirSync(new URL('../../.local/screenshots/', import.meta.url), { recursive: true })
    await page.screenshot({ path: screenshot, fullPage: true })
    console.error(
      JSON.stringify({
        errors,
        visibleState: await page.locator('main').innerText(),
        paths: await page.locator('.leaflet-overlay-pane').innerHTML(),
      }),
    )
    throw error
  }
  assert.equal(await selectedLine.count(), 1)
  assert.match(await selectedLine.getAttribute('d'), /[ML]/)
  assert(
    (await page.locator('.route-totals').innerText()).includes(
      `${route.primary.total_distance_m.toFixed(1)} m`,
    ),
  )
  mkdirSync(new URL('../../.local/screenshots/', import.meta.url), { recursive: true })
  await page.screenshot({ path: screenshot, fullPage: true })
  await page.goto('/register')
  const email = `release-browser-${crypto.randomUUID()}@example.com`
  const password = 'synthetic release browser account password'
  await page.getByLabel('Your name').fill('Release explorer')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await page.getByRole('heading', { name: 'You’re all set.' }).waitFor()
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL('**/dashboard')
  const cookie = (await context.cookies()).find((value) => value.name === '__Host-pathable_session')
  assert(cookie?.secure && cookie.httpOnly && cookie.sameSite === 'Lax')
  await page.getByRole('button', { name: /Release explorer/ }).click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.goto('/profile')
  await page.waitForURL('**/login?returnTo=*')
  assert.deepEqual(errors, [])
  console.log(
    'PASS production browser: CSP-compatible built map/route, real registration/login, Secure host cookie and logout protection',
  )
} finally {
  await browser.close()
}
