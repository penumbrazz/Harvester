import { execSync } from 'child_process'
import path from 'path'

/**
 * Playwright global teardown: remove e2e test data from the database
 * after all E2E test files have finished.
 */
async function globalTeardown() {
  const script = path.resolve(__dirname, '../../scripts/cleanup_e2e_data.py')
  console.log('\n🧹 Cleaning up e2e test data...')
  try {
    execSync(`uv run python ${script}`, {
      stdio: 'inherit',
      cwd: path.resolve(__dirname, '../..'),
    })
  } catch {
    console.error('⚠️  E2E cleanup failed — test data may remain in the database.')
  }
}

export default globalTeardown
