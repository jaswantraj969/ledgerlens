import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { FIXTURE } from './global-setup'

const PASSWORD = 'correct-horse-battery-e2e'

test('upload, review and export one invoice', async ({ page, request }) => {
  const email = `e2e-${Date.now()}@example.test`
  const registered = await request.post('/api/auth/register', {
    data: { organization: 'E2E', email, password: PASSWORD },
  })
  expect(registered.status()).toBe(201)

  await page.goto('/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible()

  await page.getByLabel('Upload documents').setInputFiles(FIXTURE)
  await expect(page.getByText('invoice.pdf: queued')).toBeVisible()
  // The worker processes it; the page polls until the job finishes.
  const status = page.locator('[data-testid^="status-"]').first()
  await expect(status).toHaveText(/ready_for_review|completed/, { timeout: 90_000 })

  await page.getByRole('link', { name: 'invoice.pdf' }).click()
  await expect(page.getByRole('img', { name: 'Page 1', exact: true })).toBeVisible()
  expect(await page.getByTestId('evidence-box').count()).toBeGreaterThan(0)

  const total = page.getByTestId('field-total_amount')
  await total.getByRole('button', { name: 'Correct' }).click()
  await total.getByLabel('Corrected value').fill('123.45')
  await total.getByRole('button', { name: 'Save' }).click()
  await expect(total).toContainText('Corrected')

  // Pin the field by its test id: a "first pending field" locator moves once it is approved.
  const firstPending = page.locator('[data-testid^="field-"]', { hasText: 'Needs review' }).first()
  if (await firstPending.count()) {
    const testId = await firstPending.getAttribute('data-testid')
    const pending = page.getByTestId(testId!)
    await pending.getByRole('button', { name: 'Approve' }).click()
    await expect(pending).toContainText('Approved')
  }

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export JSON' }).click()
  const file = await (await download).path()
  const exported = JSON.parse(readFileSync(file, 'utf-8')) as Record<string, { name: string; value_raw: string | null; decision: string }[]>
  const records = Object.values(exported)[0]
  const totalRecord = records.find((r) => r.name === 'total_amount')
  expect(totalRecord).toMatchObject({ value_raw: '123.45', decision: 'corrected' })
})
