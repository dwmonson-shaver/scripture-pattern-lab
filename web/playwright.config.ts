import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright runs against the deployed *.workers.dev URL (or a local
 * `nuxt preview`). The Worker proxies to the Render-hosted backend
 * which queries the real corpus. No mocks — by design.
 *
 * Set PLAYWRIGHT_BASE_URL before running:
 *   export PLAYWRIGHT_BASE_URL=https://scripture-pattern-lab-web.<sub>.workers.dev
 *   npm run test:e2e
 */

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium-light', use: { ...devices['Desktop Chrome'], colorScheme: 'light' } },
    { name: 'chromium-dark', use: { ...devices['Desktop Chrome'], colorScheme: 'dark' } },
  ],
})
