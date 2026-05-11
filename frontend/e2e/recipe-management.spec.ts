import { expect, test } from '@playwright/test'

test.describe('Recipe Management E2E', () => {
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

  test('navigates to the recipes page', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    await expect(page.getByRole('heading', { name: '采集配方' })).toBeVisible()
  })

  test('creates a new recipe', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    await page.getByTestId('new-recipe-button').click()
    await expect(page.getByTestId('create-recipe-form')).toBeVisible()

    const uniqueName = `e2e-recipe-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()

    await expect(page.getByTestId('create-recipe-form')).not.toBeVisible()
    await expect(page.getByText(uniqueName)).toBeVisible()
  })

  test('approves a pending recipe', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    await page.getByTestId('new-recipe-button').click()
    const uniqueName = `e2e-approve-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: uniqueName })
    await recipeRow.getByTestId(/action-approve-/).click()

    await expect(recipeRow.getByText('已批准')).toBeVisible()
  })

  test('rejects a pending recipe with confirmation', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    await page.getByTestId('new-recipe-button').click()
    const uniqueName = `e2e-reject-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: uniqueName })
    await recipeRow.getByTestId(/action-reject-/).click()

    // Confirm dialog
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByTestId('confirm-ok').click()

    await expect(recipeRow.getByText('已拒绝')).toBeVisible()
  })

  test('resubmits a rejected recipe', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    // Create and reject
    await page.getByTestId('new-recipe-button').click()
    const uniqueName = `e2e-resubmit-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: uniqueName })
    await recipeRow.getByTestId(/action-reject-/).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByTestId('confirm-ok').click()
    await expect(recipeRow.getByText('已拒绝')).toBeVisible()

    // Resubmit
    await recipeRow.getByTestId(/action-resubmit-/).click()
    await expect(recipeRow.getByText('待审批')).toBeVisible()
  })

  test('deprecates an approved recipe with confirmation', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    // Create and approve
    await page.getByTestId('new-recipe-button').click()
    const uniqueName = `e2e-deprecate-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: uniqueName })
    await recipeRow.getByTestId(/action-approve-/).click()
    await expect(recipeRow.getByText('已批准')).toBeVisible()

    // Deprecate with confirmation
    await recipeRow.getByTestId(/action-deprecate-/).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByTestId('confirm-ok').click()

    await expect(recipeRow.getByText('已废弃')).toBeVisible()
  })

  test('edits a pending recipe name', async ({ page }) => {
    await page.getByTestId('nav-recipes').click()

    await page.getByTestId('new-recipe-button').click()
    const uniqueName = `e2e-edit-recipe-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(uniqueName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(uniqueName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: uniqueName })
    await recipeRow.getByTestId(/action-edit-/).click()
    await expect(page.getByTestId(/edit-recipe-name/)).toBeVisible()

    const nameInput = page.getByTestId(/edit-recipe-name/)
    await nameInput.clear()
    await nameInput.fill(`${uniqueName}-updated`)

    await page.getByTestId(/edit-recipe-save/).click()

    await expect(page.getByText(`${uniqueName}-updated`)).toBeVisible()
  })
})
