import { test as base, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

// Cases share a disposable campus but receive independent rate-limit buckets.
// Backend integration tests separately verify the real durable quotas.
export const test = base.extend<{ resetLimits: void }>({
  resetLimits: [
    async ({ browser }, use) => {
      if (!browser.isConnected()) throw new Error('Browser is not connected')
      execFileSync(resolve('../.venv/bin/python'), [resolve('../scripts/e2e_reset_limits.py')], {
        cwd: resolve('..'),
        stdio: 'pipe',
      })
      await use()
    },
    { auto: true },
  ],
})
export { expect }
