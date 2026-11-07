import { defineConfig } from '@playwright/test'

// Runs against a running stack (docker compose up). Uses the installed Google Chrome, so no
// browser download is needed.
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  globalSetup: './e2e/global-setup.ts',
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8080',
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
  },
})
