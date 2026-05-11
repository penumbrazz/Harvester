import { expect, test } from '@playwright/test'

test.describe('Operations Observability E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and configure API connection
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()

    // Configure API base URL if not already configured
    const configForm = page.getByTestId('api-config-form')
    if (await configForm.isVisible()) {
      await page.getByTestId('input-api-base-url').fill('http://localhost:8001')
      await page.getByTestId('input-api-token').fill('test-secret')
      await page.getByTestId('save-config-button').click()
    }
  })

  test('navigates to the crawls page', async ({ page }) => {
    await page.getByTestId('nav-crawls').click()

    await expect(page.getByTestId('page-crawls')).toBeVisible()
    await expect(page.getByText('Crawls')).toBeVisible()
    await expect(page.getByTestId('trigger-crawl-button')).toBeVisible()
  })

  test('crawls page shows status filter and table', async ({ page }) => {
    await page.getByTestId('nav-crawls').click()
    await expect(page.getByTestId('page-crawls')).toBeVisible()

    await expect(page.getByTestId('select-crawl-status-filter')).toBeVisible()
  })

  test('crawls page shows trigger crawl form', async ({ page }) => {
    await page.getByTestId('nav-crawls').click()
    await expect(page.getByTestId('page-crawls')).toBeVisible()

    await page.getByTestId('trigger-crawl-button').click()
    await expect(page.getByTestId('trigger-crawl-form')).toBeVisible()
    await expect(page.getByTestId('select-source')).toBeVisible()
    await expect(page.getByTestId('select-approved-recipe')).toBeVisible()
  })

  test('crawls page form can be cancelled', async ({ page }) => {
    await page.getByTestId('nav-crawls').click()
    await expect(page.getByTestId('page-crawls')).toBeVisible()

    await page.getByTestId('trigger-crawl-button').click()
    await expect(page.getByTestId('trigger-crawl-form')).toBeVisible()

    await page.getByTestId('cancel-trigger-crawl').click()
    await expect(page.getByTestId('trigger-crawl-form')).not.toBeVisible()
  })

  test('navigates to the jobs page', async ({ page }) => {
    await page.getByTestId('nav-jobs').click()

    await expect(page.getByTestId('page-jobs')).toBeVisible()
    await expect(page.getByText('Job Queue')).toBeVisible()
  })

  test('jobs page shows filters', async ({ page }) => {
    await page.getByTestId('nav-jobs').click()
    await expect(page.getByTestId('page-jobs')).toBeVisible()

    await expect(page.getByTestId('select-job-type-filter')).toBeVisible()
    await expect(page.getByTestId('select-job-status-filter')).toBeVisible()
    await expect(page.getByTestId('select-job-lane-filter')).toBeVisible()
  })

  test('jobs page shows summary cards', async ({ page }) => {
    await page.getByTestId('nav-jobs').click()
    await expect(page.getByTestId('page-jobs')).toBeVisible()

    // Summary cards should render after data loads
    await expect(page.getByTestId('jobs-summary')).toBeVisible({ timeout: 10000 })
  })
})
