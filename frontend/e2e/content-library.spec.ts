import { expect, test } from '@playwright/test'

test.describe('Content Library E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()

    const configForm = page.getByTestId('api-config-form')
    if (await configForm.isVisible()) {
      await page.getByTestId('input-api-base-url').fill('http://localhost:8001')
      await page.getByTestId('input-api-token').fill('test-secret')
      await page.getByTestId('save-config-button').click()
    }
  })

  test('navigates to the content library page and renders the heading', async ({
    page,
  }) => {
    await page.getByTestId('nav-content').click()

    await expect(page.getByTestId('page-content-library')).toBeVisible()
    await expect(
      page.getByRole('heading', { name: '内容库' }),
    ).toBeVisible()
  })

  test('shows empty state when no content items exist', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()

    // Wait for loading to finish
    await expect(page.getByTestId('content-loading')).not.toBeVisible()

    // Empty state should appear
    await expect(page.getByTestId('content-empty')).toBeVisible()
    await expect(page.getByText('未找到内容项')).toBeVisible()
  })

  test('displays search input and mode selector', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()

    await expect(page.getByTestId('search-input')).toBeVisible()
    await expect(page.getByTestId('search-mode-select')).toBeVisible()
    await expect(page.getByTestId('search-button')).toBeVisible()
  })

  test('displays filter controls for type and status', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()

    await expect(page.getByTestId('select-type-filter')).toBeVisible()
    await expect(page.getByTestId('select-status-filter')).toBeVisible()
  })

  test('displays view toggle buttons for list and grid', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()

    await expect(page.getByTestId('view-list')).toBeVisible()
    await expect(page.getByTestId('view-grid')).toBeVisible()
  })

  test('performs a keyword search', async ({ page }) => {
    await page.getByTestId('nav-content').click()
    await expect(page.getByTestId('page-content-library')).toBeVisible()

    await page.getByTestId('search-input').fill('test query')
    await page.getByTestId('search-button').click()

    // Search results container should appear (or loading indicator)
    await expect(
      page.getByTestId('search-loading').or(page.getByTestId('search-results')),
    ).toBeVisible()

    // Clear button should be visible during search
    await expect(page.getByTestId('search-clear')).toBeVisible()

    // Clear the search
    await page.getByTestId('search-clear').click()
    await expect(page.getByTestId('search-results')).not.toBeVisible()
  })
})
