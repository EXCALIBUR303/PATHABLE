import { defineConfig, devices } from '@playwright/test'
import { existsSync } from 'node:fs'

const executable =
  process.env.PATHABLE_CHROMIUM_PATH ??
  (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined)
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://localhost:5174',
    viewport: { width: 1440, height: 960 },
    locale: 'en-GB',
    timezoneId: 'Asia/Kolkata',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: { ...(executable ? { executablePath: executable } : {}) },
  },
  webServer: [
    {
      command: '../.venv/bin/python ../scripts/e2e_backend.py',
      url: 'http://127.0.0.1:18000/api/v1/health/ready',
      reuseExistingServer: false,
      timeout: 60_000,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
    },
    {
      command: 'npm run dev -- --port 5174',
      env: { API_PORT: '18000' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 60_000,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
    },
  ],
})
