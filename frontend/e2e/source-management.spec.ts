import { expect, test } from '@playwright/test'

test.describe('Source Management E2E', () => {
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

  test('navigates to the sources page', async ({ page }) => {
    await page.getByTestId('nav-sources').click()

    await expect(page.getByTestId('page-sources')).toBeVisible()
    await expect(page.getByText('Sources')).toBeVisible()
    await expect(page.getByText(/Candidate.*Testing.*Watched/)).toBeVisible()
  })

  test('creates a new source via the propose form', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    // Open the propose form
    await page.getByTestId('new-source-button').click()
    await expect(page.getByTestId('propose-source-form')).toBeVisible()

    // Fill in the form with a unique name
    const uniqueName = `e2e-src-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('input-source-url').fill('https://e2e-test.example.com')

    // Submit
    await page.getByTestId('submit-propose-source').click()

    // Verify the form closes and the source appears in the table
    await expect(page.getByTestId('propose-source-form')).not.toBeVisible()
    await expect(page.getByText(uniqueName)).toBeVisible()
  })

  test('shows validation error for empty source name', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    await page.getByTestId('submit-propose-source').click()

    await expect(page.getByTestId('propose-source-error')).toBeVisible()
  })

  test('promotes a candidate source to testing', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    // Create a new source
    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-promote-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()

    // Wait for the source to appear
    await expect(page.getByText(uniqueName)).toBeVisible()

    // Find the promote button for this source and click it
    const sourceRow = page.locator('tr', { hasText: uniqueName })
    const promoteButton = sourceRow.getByTestId(/action-promote-/)
    await expect(promoteButton).toBeVisible()
    await promoteButton.click()

    // Verify the status changed to testing
    await expect(sourceRow.getByText('Testing')).toBeVisible()
  })

  test('pauses a watched source', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    // Create and promote to watched
    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-pause-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const sourceRow = page.locator('tr', { hasText: uniqueName })

    // Promote twice: candidate -> testing -> watched
    await sourceRow.getByTestId(/action-promote-/).click()
    await expect(sourceRow.getByText('Testing')).toBeVisible()
    await sourceRow.getByTestId(/action-promote-/).click()
    await expect(sourceRow.getByText('Watched')).toBeVisible()

    // Now pause
    await sourceRow.getByTestId(/action-pause-/).click()
    await expect(sourceRow.getByText('Paused')).toBeVisible()
  })

  test('filters sources by status', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    // Create a source
    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-filter-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    // Filter by candidate status
    await page.getByTestId('select-status-filter').selectOption('candidate')

    // Our new source should be visible (it's a candidate)
    await expect(page.getByText(uniqueName)).toBeVisible()
  })

  test('searches sources by name', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    // Create a source with a distinctive name
    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-search-xyz-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    // Search for it
    await page.getByTestId('input-source-search').fill('e2e-search-xyz')
    await expect(page.getByText(uniqueName)).toBeVisible()
  })
})
