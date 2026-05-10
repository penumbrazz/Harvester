import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DashboardSummary } from '../../../types/observability'
import { DashboardPage } from '../dashboard-page'

const config = {
  baseUrl: 'http://localhost:8001',
  token: 'test-token',
}

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

/** Helper to mock a successful JSON response. */
function mockJsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

const mockSummary: DashboardSummary = {
  sources: { total: 5, by_status: { watched: 3, paused: 2 } },
  crawl_runs: { total: 10, by_status: { completed: 8, failed: 2 } },
  jobs: { total: 20, by_status: { pending: 10, completed: 8, failed: 2 } },
  content_items: { total: 100, by_status: { active: 100 } },
  failures: { total: 4, by_status: { failed_crawl_runs: 2, failed_jobs: 2 } },
  audit_events: { total: 50, by_status: {} },
}

const mockFailures = {
  crawl_runs: [
    {
      id: 'fail-1',
      entity_type: 'crawl_run',
      status: 'failed',
      error_message: 'Connection timeout',
      created_at: '2026-01-01T10:00:00Z',
    },
  ],
  jobs: [
    {
      id: 'fail-2',
      entity_type: 'job',
      status: 'dead',
      error_message: 'Max attempts reached',
      created_at: '2026-01-01T11:00:00Z',
    },
  ],
}

describe('DashboardPage', () => {
  it('renders the page title and refresh button', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<DashboardPage config={config} />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByTestId('refresh-dashboard')).toBeInTheDocument()
  })

  it('shows loading state while fetching data', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<DashboardPage config={config} />)

    expect(screen.getByTestId('dashboard-loading')).toBeInTheDocument()
  })

  it('displays metric cards after loading', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockSummary))
      .mockResolvedValueOnce(mockJsonResponse(mockFailures))

    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-metrics')).toBeInTheDocument()
    })

    expect(screen.getByText('Sources')).toBeInTheDocument()
    expect(screen.getByText('Crawl Runs')).toBeInTheDocument()
    expect(screen.getByText('Jobs')).toBeInTheDocument()
    expect(screen.getByText('Content Items')).toBeInTheDocument()
    expect(screen.getByText('Failures')).toBeInTheDocument()
    expect(screen.getByText('Audit Events')).toBeInTheDocument()
  })

  it('shows metric values from API response', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockSummary))
      .mockResolvedValueOnce(mockJsonResponse(mockFailures))

    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
  })

  it('displays recent failures panel', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockSummary))
      .mockResolvedValueOnce(mockJsonResponse(mockFailures))

    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getAllByText('Recent Failures').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText('Connection timeout')).toBeInTheDocument()
    expect(screen.getByText('Max attempts reached')).toBeInTheDocument()
  })

  it('shows no failures message when empty', async () => {
    const emptySummary = {
      ...mockSummary,
      failures: { total: 0, by_status: {} },
    }
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(emptySummary))
      .mockResolvedValueOnce(mockJsonResponse({ crawl_runs: [], jobs: [] }))

    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-no-failures')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })

    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-error')).toBeInTheDocument()
    })
  })

  it('refreshes data when refresh button is clicked', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockSummary))
      .mockResolvedValueOnce(mockJsonResponse(mockFailures))
      .mockResolvedValueOnce(mockJsonResponse(mockSummary))
      .mockResolvedValueOnce(mockJsonResponse(mockFailures))

    const user = userEvent.setup()
    render(<DashboardPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-metrics')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('refresh-dashboard'))

    // Should have been called more times
    expect(mockFetch.mock.calls.length).toBeGreaterThan(2)
  })
})
