import { expect, test } from '@playwright/test'

test.describe('Schedule Management E2E', () => {
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

  test('navigates to the schedules page', async ({ page }) => {
    await page.getByTestId('nav-schedules').click()

    await expect(page.getByRole('heading', { name: '调度计划' })).toBeVisible()
  })

  test('creates a new schedule', async ({ page }) => {
    // Create a watched source
    await page.getByTestId('nav-sources').click()
    await page.getByTestId('new-source-button').click()
    const srcName = `e2e-sch-src-${Date.now()}`
    await page.getByTestId('input-source-name').fill(srcName)
    await page.getByTestId('submit-propose-source').click()
    await expect(page.getByText(srcName)).toBeVisible()

    const srcRow = page.locator('tr', { hasText: srcName })
    // candidate -> testing -> watched
    await srcRow.getByTestId(/action-promote-/).click()
    await expect(srcRow.getByText('测试中')).toBeVisible()
    await srcRow.getByTestId(/action-promote-/).click()
    await expect(srcRow.getByText('监控中')).toBeVisible()

    // Create and approve a recipe
    await page.getByTestId('nav-recipes').click()
    await page.getByTestId('new-recipe-button').click()
    const recipeName = `e2e-sch-recipe-${Date.now()}`
    await page.getByTestId('input-recipe-name').fill(recipeName)
    await page.getByTestId('select-recipe-executor').selectOption('http_fetch')
    await page.getByTestId('submit-create-recipe').click()
    await expect(page.getByText(recipeName)).toBeVisible()

    const recipeRow = page.locator('tr', { hasText: recipeName })
    await recipeRow.getByTestId(/action-approve-/).click()
    await expect(recipeRow.getByText('已批准')).toBeVisible()

    // Create schedule
    await page.getByTestId('nav-schedules').click()
    await expect(page.getByRole('heading', { name: '调度计划' })).toBeVisible()
    await page.getByTestId('new-schedule-button').click()
    await expect(page.getByTestId('create-schedule-form')).toBeVisible()

    await page.getByTestId('select-schedule-source').selectOption({ index: 1 })
    await page.getByTestId('select-schedule-recipe').selectOption({ index: 1 })
    await page.getByTestId('input-schedule-interval').fill('3600')
    await page.getByTestId('submit-create-schedule').click()

    await expect(page.getByTestId('create-schedule-form')).not.toBeVisible()
    // The new schedule should appear with 活跃 status
    await expect(page.locator('tr').filter({ hasText: '活跃' }).first()).toBeVisible()
  })

  test('pauses and resumes an active schedule', async ({ page }) => {
    await page.getByTestId('nav-schedules').click()
    await expect(page.getByRole('heading', { name: '调度计划' })).toBeVisible()

    // Find an active schedule row
    const activeRow = page.locator('tr', { hasText: '活跃' }).first()
    if (await activeRow.isVisible()) {
      const pauseBtn = activeRow.getByTestId(/action-pause-/)
      if (await pauseBtn.isVisible()) {
        await pauseBtn.click()
        await expect(activeRow.getByText('已暂停')).toBeVisible()

        // Resume
        const resumeBtn = activeRow.getByTestId(/action-resume-/)
        await resumeBtn.click()
        await expect(activeRow.getByText('活跃')).toBeVisible()
      }
    }
  })

  test('disables a schedule with confirmation', async ({ page }) => {
    await page.getByTestId('nav-schedules').click()
    await expect(page.getByRole('heading', { name: '调度计划' })).toBeVisible()

    const activeRow = page.locator('tr', { hasText: '活跃' }).first()
    if (await activeRow.isVisible()) {
      const disableBtn = activeRow.getByTestId(/action-disable-/)
      if (await disableBtn.isVisible()) {
        await disableBtn.click()

        // Confirm dialog
        await expect(page.getByRole('dialog')).toBeVisible()
        await page.getByTestId('confirm-ok').click()

        await expect(activeRow.getByText('已停用')).toBeVisible()
      }
    }
  })

  test('edits a schedule interval', async ({ page }) => {
    await page.getByTestId('nav-schedules').click()
    await expect(page.getByRole('heading', { name: '调度计划' })).toBeVisible()

    const activeRow = page.locator('tr', { hasText: '活跃' }).first()
    if (await activeRow.isVisible()) {
      const editBtn = activeRow.getByTestId(/action-edit-/)
      if (await editBtn.isVisible()) {
        await editBtn.click()
        await expect(page.getByTestId(/edit-schedule-interval/)).toBeVisible()

        const intervalInput = page.getByTestId(/edit-schedule-interval/)
        await intervalInput.clear()
        await intervalInput.fill('7200')

        await page.getByTestId(/edit-schedule-save/).click()

        await expect(activeRow.getByText('2h')).toBeVisible()
      }
    }
  })
})
