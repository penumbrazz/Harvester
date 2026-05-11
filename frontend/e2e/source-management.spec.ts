import { expect, test } from '@playwright/test'

test.describe('Source Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
    await page.reload()

    const configForm = page.getByTestId('api-config-form')
    if (await configForm.isVisible()) {
      await page.getByTestId('input-api-base-url').fill('http://localhost:8001')
      await page.getByTestId('input-api-token').fill('change-me-in-production')
      await page.getByTestId('save-config-button').click()
    }
  })

  test('navigates to the sources page', async ({ page }) => {
    await page.getByTestId('nav-sources').click()

    await expect(page.getByTestId('page-sources')).toBeVisible()
    await expect(page.getByRole('heading', { name: '信息源' })).toBeVisible()
  })

  test('creates a new source via the propose form', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    await expect(page.getByTestId('propose-source-form')).toBeVisible()

    const uniqueName = `e2e-src-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('input-source-url').fill('https://e2e-test.example.com')

    await page.getByTestId('submit-propose-source').click()

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

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-promote-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()

    await expect(page.getByText(uniqueName)).toBeVisible()

    const sourceRow = page.locator('tr', { hasText: uniqueName })
    const promoteButton = sourceRow.getByTestId(/action-promote-/)
    await expect(promoteButton).toBeVisible()
    await promoteButton.click()

    await expect(sourceRow.getByText('测试中')).toBeVisible()
  })

  test('pauses a watched source', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-pause-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const sourceRow = page.locator('tr', { hasText: uniqueName })

    // candidate -> testing -> watched
    await sourceRow.getByTestId(/action-promote-/).click()
    await expect(sourceRow.getByText('测试中')).toBeVisible()
    await sourceRow.getByTestId(/action-promote-/).click()
    await expect(sourceRow.getByText('监控中')).toBeVisible()

    // watched -> paused
    await sourceRow.getByTestId(/action-pause-/).click()
    await expect(sourceRow.getByText('已暂停')).toBeVisible()
  })

  test('edits a source name', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-edit-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const sourceRow = page.locator('tr', { hasText: uniqueName })

    // Click edit button
    await sourceRow.getByTestId(/action-edit-/).click()
    await expect(page.getByTestId(/edit-source-name/)).toBeVisible()

    // Change name
    const nameInput = page.getByTestId(/edit-source-name/)
    await nameInput.clear()
    await nameInput.fill(`${uniqueName}-updated`)

    // Save
    await page.getByTestId(/edit-source-save/).click()

    // Verify updated name appears
    await expect(page.getByText(`${uniqueName}-updated`)).toBeVisible()
  })

  test('archives a candidate source with confirmation', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-archive-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const sourceRow = page.locator('tr', { hasText: uniqueName })

    // Click archive
    await sourceRow.getByTestId(/action-archive-/).click()

    // Confirm dialog should appear
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText(`确定要归档信息源「${uniqueName}」吗？`)).toBeVisible()

    // Confirm
    await page.getByTestId('confirm-ok').click()

    // Should be archived
    await expect(sourceRow.getByText('已归档')).toBeVisible()
  })

  test('filters sources by status', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-filter-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    await page.getByTestId('select-status-filter').selectOption('候选')

    await expect(page.getByText(uniqueName)).toBeVisible()
  })

  test('searches sources by name', async ({ page }) => {
    await page.getByTestId('nav-sources').click()
    await expect(page.getByTestId('page-sources')).toBeVisible()

    await page.getByTestId('new-source-button').click()
    const uniqueName = `e2e-search-xyz-${Date.now()}`
    await page.getByTestId('input-source-name').fill(uniqueName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    await page.getByTestId('input-source-search').fill('e2e-search-xyz')
    await expect(page.getByText(uniqueName)).toBeVisible()
  })
})
