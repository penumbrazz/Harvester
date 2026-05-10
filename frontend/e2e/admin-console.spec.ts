import { expect, test } from '@playwright/test'

test.describe('Admin Console E2E', () => {
  test('opens the admin console and shows the overview page', async ({
    page,
  }) => {
    await page.goto('/')

    // Verify the app shell renders
    await expect(page.getByTestId('app-layout')).toBeVisible()
    await expect(page.getByTestId('sidebar')).toBeVisible()
    await expect(page.getByTestId('page-overview')).toBeVisible()

    // Verify the Harvester brand title
    await expect(page.getByText('Harvester')).toBeVisible()
  })

  test('renders all navigation items in the sidebar', async ({ page }) => {
    await page.goto('/')

    const expectedItems = [
      'overview',
      'sources',
      'recipes',
      'schedules',
      'crawls',
      'jobs',
      'content',
      'audit',
    ]

    for (const key of expectedItems) {
      await expect(page.getByTestId(`nav-${key}`)).toBeVisible()
    }
  })

  test('navigates between pages without full page reload', async ({ page }) => {
    await page.goto('/')

    // Click Sources nav item
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()
    await expect(page.getByTestId('page-overview')).not.toBeVisible()

    // Click Recipes nav item
    await page.getByTestId('nav-recipes').click()
    await expect(page.getByTestId('page-recipes')).toBeVisible()

    // Click Overview to go back
    await page.getByTestId('nav-overview').click()
    await expect(page.getByTestId('page-overview')).toBeVisible()
  })

  test('shows API configuration form when no URL is configured', async ({
    page,
  }) => {
    // Clear any existing config
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()

    // The config form should be visible since no URL is configured
    await expect(page.getByTestId('api-config-form')).toBeVisible()
    await expect(page.getByTestId('input-api-base-url')).toBeVisible()
    await expect(page.getByTestId('input-api-token')).toBeVisible()
  })

  test('configures API base URL and token', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()

    // Fill in the API configuration
    await page.getByTestId('input-api-base-url').fill('http://localhost:8001')
    await page.getByTestId('input-api-token').fill('test-token-123')
    await page.getByTestId('save-config-button').click()

    // After saving, the display mode should show the configured URL
    await expect(page.getByTestId('api-config-display')).toBeVisible()
    await expect(page.getByText('http://localhost:8001')).toBeVisible()
  })
})
