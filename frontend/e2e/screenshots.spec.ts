import { expect, test } from '@playwright/test'
import { readdirSync } from 'node:fs'
import { join } from 'node:path'

// Portfolio screenshots of the running app. Skipped unless SCREENSHOT_DIR (where to write the
// PNG files) and SCREENSHOT_INPUTS (a folder of sample receipts) are both set.
const OUT = process.env.SCREENSHOT_DIR
const INPUTS = process.env.SCREENSHOT_INPUTS
const PASSWORD = 'correct-horse-battery-screens'

test.skip(!OUT || !INPUTS, 'set SCREENSHOT_DIR and SCREENSHOT_INPUTS to take screenshots')
test.use({ viewport: { width: 1440, height: 900 } })

test('portfolio screenshots', async ({ page, request }) => {
  test.setTimeout(240_000)
  const email = `screens-${Date.now()}@example.test`
  const registered = await request.post('/api/auth/register', {
    data: { organization: 'Screenshots', email, password: PASSWORD },
  })
  expect(registered.status()).toBe(201)

  await page.goto('/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible()

  const files = readdirSync(INPUTS!).sort().map((name) => join(INPUTS!, name))
  await page.getByLabel('Upload documents').setInputFiles(files)
  const statuses = page.locator('[data-testid^="status-"]')
  await expect(statuses).toHaveCount(files.length)
  for (let index = 0; index < files.length; index++) {
    await expect(statuses.nth(index)).toHaveText(/ready_for_review|completed|failed/, { timeout: 120_000 })
  }
  await page.screenshot({ path: join(OUT!, '1-documents.png') })

  await page.locator('a[href^="#/documents/"]').first().click()
  await expect(page.getByRole('img', { name: 'Page 1' }).first()).toBeVisible()
  await page.waitForTimeout(500)
  await page.screenshot({ path: join(OUT!, '2-review.png'), fullPage: true })

  // Use the app's own navigation, and wait for each page's content, not just the network.
  await page.getByRole('link', { name: 'Review queue' }).click()
  await expect(page.getByRole('heading', { name: 'Review queue' }).or(page.getByRole('alert'))).toBeVisible()
  await page.screenshot({ path: join(OUT!, '3-queue.png') })

  await page.getByRole('link', { name: 'Evaluation' }).click()
  await expect(page.getByRole('heading', { name: 'Evaluation report' }).or(page.getByRole('alert'))).toBeVisible()
  await page.screenshot({ path: join(OUT!, '4-report.png'), fullPage: true })
})
