import { test, expect } from '@playwright/test'

/**
 * Slice J1 exit gate: a real NL query goes through the Worker proxy to
 * the Render-hosted FastAPI backend and renders a structured envelope
 * in the browser. No mocks at any layer.
 *
 * Setup required before running:
 *   - The Worker is deployed (or `npm run preview` is up locally).
 *   - The Render backend is up with SPL_BEARER_TOKEN set, DATABASE_URL
 *     pointing at a Postgres with the corpus + registry loaded.
 *   - The Worker has NUXT_BACKEND_URL and NUXT_BACKEND_TOKEN secrets set
 *     matching the Render service.
 */

const FLAGSHIP_QUESTION =
  'Where do faith, hope, and love appear together in proximity with precedence?'

test.describe('Slice J1 golden path', () => {
  test('flagship NL query renders the deterministic envelope', async ({ page }) => {
    await page.goto('/')

    // The page renders.
    await expect(page.getByRole('heading', { level: 6 })).toContainText(
      /symbolic pattern queries/i,
    )

    // The user types the flagship question and submits.
    const textarea = page.getByTestId('query-input').locator('textarea')
    await textarea.fill(FLAGSHIP_QUESTION)

    const runBtn = page.getByTestId('query-run')
    await expect(runBtn).toBeEnabled()
    await runBtn.click()

    // The result envelope arrives. Generous timeout because the path is
    // browser → Worker → Render → Postgres → Render → Worker → browser
    // and includes a live LLM compile step.
    const envelope = page.getByTestId('result-envelope')
    await expect(envelope).toBeVisible({ timeout: 20_000 })

    // The flagship verse is in there.
    await expect(envelope).toContainText('1Cor 13:13')

    // Greek text rendered via <GreekText> (SBL Greek font; lemmas present).
    const greekRegions = page.getByTestId('greek-text')
    await expect(greekRegions.first()).toBeVisible()
    const greekText = (await greekRegions.allTextContents()).join(' ')
    expect(greekText).toMatch(/π[ίι]στις|ἐλπίς|ἀγάπη/u)

    // Contextualization shows the three node baselines.
    const ctxCard = page.getByTestId('contextualization-card')
    await expect(ctxCard).toBeVisible()
    await expect(ctxCard).toContainText(/observed.*2 match/i)

    // Validation status visible and not "unsupported".
    const statusChip = page.getByTestId('validation-status')
    await expect(statusChip).toBeVisible()
    const status = (await statusChip.textContent())?.trim().toLowerCase() ?? ''
    expect(status).toMatch(/supported|partial/)
    expect(status).not.toBe('unsupported')

    // Explanation summary is non-empty and ≤5 non-blank lines (DEC-061).
    const summary = page.getByTestId('explanation-summary')
    await expect(summary).toBeVisible()
    const summaryText = (await summary.textContent()) ?? ''
    const nonBlankLines = summaryText.split('\n').filter((l) => l.trim().length > 0)
    expect(nonBlankLines.length).toBeGreaterThan(0)
    expect(nonBlankLines.length).toBeLessThanOrEqual(5)
  })

  test('Run button stays disabled on an empty query', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('query-run')).toBeDisabled()
  })

  test('theme toggle switches background between modes', async ({ page }) => {
    await page.goto('/')

    const bg1 = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
    const toggleBtn = page.getByRole('button', { name: /switch to (light|dark) mode/i })
    await toggleBtn.click()
    // Wait a paint frame.
    await page.waitForTimeout(100)
    const bg2 = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)

    expect(bg1).not.toEqual(bg2)
  })
})
